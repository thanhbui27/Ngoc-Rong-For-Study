"""Clone client-visible NRO assets from a user-supplied server address."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from decode_game_data import NAMES, decode_directory, referenced_image_ids
from decode_item_packets import decode_directory as decode_items
from nro_wire import NroWire, modified_utf, safe_relative_path

PNG = b"\x89PNG\r\n\x1a\n"


def save(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(data)
    temporary.replace(path)


def connect(host: str, port: int, zoom: int, version: str, timeout: float, require_resources: bool = True):
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        sock.settimeout(timeout)
        wire = NroWire(sock)
        wire.send(-27)
        command, payload = wire.read()
        if command != -27:
            raise ValueError(f"Expected handshake -27, got {command}")
        route = wire.accept_key(payload)
        platform = f"pc|{version}".encode("ascii")
        info = bytes((2, 4, zoom, 0)) + struct.pack(">ii", 1280, 720) + bytes((0, 1))
        info += struct.pack(">H", len(platform)) + platform
        wire.send(-29, info)
        if not require_resources:
            return sock, wire, {"route": route, "resource_version": None, "image_versions": None}
        image_versions = None
        for _ in range(100):
            command, payload = wire.read()
            if command == -77 and len(payload) >= 2:
                count = struct.unpack_from(">h", payload)[0]
                if count >= 0 and len(payload) == count + 2:
                    image_versions = list(payload[2:])
            if command == -74 and len(payload) >= 5 and payload[0] == 0:
                resource_version = struct.unpack_from(">i", payload, 1)[0]
                return sock, wire, {"route": route, "resource_version": resource_version,
                                    "image_versions": image_versions}
        raise TimeoutError("No resource-version announcement after handshake")
    except Exception:
        sock.close()
        raise


def await_command(wire: NroWire, wanted: int, max_packets: int = 100) -> bytes:
    for _ in range(max_packets):
        command, payload = wire.read()
        if command == wanted:
            return payload
    raise TimeoutError(f"No response for command {wanted}")


def get_game_data(wire: NroWire, out: Path) -> dict:
    wire.send(-87)
    payload = await_command(wire, -87)
    if not payload:
        raise ValueError("Empty update-data packet")
    position = 1
    blobs = {}
    for name in NAMES:
        if position + 4 > len(payload):
            raise ValueError(f"Missing {name} length")
        size = struct.unpack_from(">i", payload, position)[0]
        position += 4
        if size < 0 or position + size > len(payload):
            raise ValueError(f"Invalid {name} length {size}")
        blob = payload[position:position + size]
        blobs[name] = blob
        position += size
    trailing = payload[position:]
    save(out / "raw" / "update-data.packet", payload)
    for name, blob in blobs.items():
        save(out / "game-data" / f"{name}.bin", blob)
    if trailing:
        save(out / "raw" / "update-data-trailing.bin", trailing)
    decoded = decode_directory(out / "game-data", out / "decoded")
    return {"version": payload[0], "bytes": len(payload),
            "unknown_trailing_bytes": len(trailing), "decoded": decoded}


def get_resources(wire: NroWire, out: Path, zoom: int, max_files: int | None) -> dict:
    wire.send(-74, b"\x01")
    announced = None
    received = 0
    saved = 0
    total_bytes = 0
    files = []
    complete = False
    while True:
        command, payload = wire.read()
        if command != -74 or not payload:
            continue
        action = payload[0]
        if action == 1:
            if len(payload) < 3:
                raise ValueError("Truncated resource manifest")
            announced = struct.unpack_from(">H", payload, 1)[0]
            wire.send(-74, b"\x02")
        elif action == 2:
            path_text, position = modified_utf(payload, 1)
            if position + 4 > len(payload):
                raise ValueError("Truncated resource size")
            size = struct.unpack_from(">i", payload, position)[0]
            blob = payload[position + 4:]
            if size < 0 or size != len(blob):
                raise ValueError(f"Invalid resource size for {path_text}")
            relative = safe_relative_path(path_text)
            if not relative.suffix:
                relative = relative.with_suffix(".png")
            destination = out / "resources" / f"zoom{zoom}" / relative
            if not destination.is_file() or hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(blob).digest():
                save(destination, blob)
                saved += 1
            files.append({"path": str(relative).replace("\\", "/"), "bytes": size,
                          "sha256": hashlib.sha256(blob).hexdigest()})
            received += 1
            total_bytes += size
            if received % 100 == 0:
                print(f"  zoom {zoom}: {received}/{announced or '?'} resources", flush=True)
            if max_files is not None and received >= max_files:
                break
        elif action == 3:
            complete = True
            break
    save(out / "manifests" / f"resources-zoom{zoom}.json",
         json.dumps(files, ensure_ascii=False, indent=2).encode("utf-8"))
    return {"announced": announced, "received": received, "saved": saved,
            "bytes": total_bytes, "stream_ended": complete,
            "complete": complete and (announced is None or announced == received)}


def get_icons(host: str, port: int, out: Path, zoom: int, version: str,
              timeout: float, ids: list[int], batch_size: int) -> dict:
    folder = out / "icons" / f"zoom{zoom}"
    missing = []
    saved = 0
    existing = 0
    for offset in range(0, len(ids), batch_size):
        batch = ids[offset:offset + batch_size]
        pending = [item for item in batch if not (folder / f"{item}.png").is_file()]
        existing += len(batch) - len(pending)
        if not pending:
            continue
        try:
            sock, wire, _ = connect(host, port, zoom, version, timeout)
            try:
                sock.settimeout(min(timeout, 3))
                for image_id in pending:
                    wire.send(-67, struct.pack(">i", image_id))
                    time.sleep(0.02)
                unanswered = set(pending)
                while unanswered:
                    try:
                        command, payload = wire.read()
                    except (socket.timeout, ConnectionError, OSError):
                        break
                    if command != -67 or len(payload) < 8:
                        continue
                    image_id, length = struct.unpack_from(">ii", payload)
                    if image_id not in unanswered:
                        continue
                    unanswered.remove(image_id)
                    blob = payload[8:]
                    if length == len(blob) and blob.startswith(PNG):
                        save(folder / f"{image_id}.png", blob)
                        saved += 1
                missing.extend(sorted(unanswered))
            finally:
                sock.close()
        except (OSError, TimeoutError, ConnectionError) as error:
            print(f"  zoom {zoom}: icon batch {offset} failed: {error}", file=sys.stderr)
            missing.extend(pending)
        if (offset // batch_size) % 10 == 0 or offset + batch_size >= len(ids):
            print(f"  zoom {zoom}: {min(offset + batch_size, len(ids))}/{len(ids)} image IDs", flush=True)
    save(out / "manifests" / f"missing-icons-zoom{zoom}.txt",
         ("\n".join(map(str, missing)) + ("\n" if missing else "")).encode("ascii"))
    return {"requested": len(ids), "saved": saved, "existing": existing,
            "missing": len(missing), "complete": not missing}


def get_update_packets(wire: NroWire, out: Path, subcommands: tuple[int, ...]) -> dict:
    results = {}
    for subcommand in subcommands:
        wire.send(-28, bytes((subcommand,)))
        packets = []
        old_timeout = wire.sock.gettimeout()
        wire.sock.settimeout(2)
        try:
            for _ in range(40):
                try:
                    command, payload = wire.read()
                except socket.timeout:
                    break
                if command == -28 and payload and payload[0] == subcommand:
                    packets.append(payload)
                elif packets:
                    break
        finally:
            wire.sock.settimeout(old_timeout)
        for index, payload in enumerate(packets):
            save(out / "raw" / "updates" / f"sub{subcommand}-{index:03}.bin", payload)
        results[str(subcommand)] = {"packets": len(packets), "bytes": sum(map(len, packets))}
    return results


def get_maps(host: str, port: int, zoom: int, version: str,
             timeout: float, out: Path) -> dict:
    source = out / "raw" / "updates" / "sub6-000.bin"
    if not source.is_file():
        return {"status": "no_map_update_packet"}
    payload = source.read_bytes()
    if len(payload) < 3 or payload[0] != 6:
        return {"status": "invalid_map_update_packet"}
    count = payload[2]
    position = 3
    names = []
    for _ in range(count):
        name, position = modified_utf(payload, position)
        names.append(name)
    save(out / "decoded" / "map-names.json",
         (json.dumps(names, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    saved, existing, missing = 0, 0, []
    sock = None
    try:
        for map_id in range(count):
            target = out / "raw" / "maps" / f"{map_id:03}.bin"
            if target.is_file():
                existing += 1
                continue
            try:
                if sock is None:
                    sock, wire, _ = connect(host, port, zoom, version, timeout)
                    sock.settimeout(min(timeout, 3))
                wire.send(-28, bytes((10, map_id)))
                for _ in range(20):
                    command, reply = wire.read()
                    if command == -28 and reply[:1] == b"\x0a":
                        save(target, reply)
                        saved += 1
                        break
                else:
                    missing.append(map_id)
            except (OSError, TimeoutError, ConnectionError):
                missing.append(map_id)
                if sock is not None:
                    sock.close()
                    sock = None
            if (map_id + 1) % 50 == 0:
                print(f"  maps: {map_id + 1}/{count}", flush=True)
    finally:
        if sock is not None:
            sock.close()
    return {"announced": count, "saved": saved, "existing": existing,
            "available": saved + existing, "missing": missing,
            "complete": not missing and saved + existing == count,
            "path": str(out / "raw" / "maps")}


def parse_address(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"(?:([\w.-]+)|\[([0-9a-fA-F:]+)\]):(\d{1,5})", value.strip())
    if not match:
        raise ValueError("Server must be HOST:PORT")
    port = int(match[3])
    if not 1 <= port <= 65535:
        raise ValueError("Port must be 1..65535")
    return match[1] or match[2], port


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", help="NRO game server HOST:PORT; prompted when omitted")
    parser.add_argument("--out", type=Path, help="Capture directory (default: ../NRO-clones/HOST-PORT)")
    parser.add_argument("--zooms", default="1,2,3,4", help="Comma-separated client zooms, default 1,2,3,4")
    parser.add_argument("--version", default="2.3.1", help="PC client version")
    parser.add_argument("--icons", choices=("all", "referenced", "none"), default="all")
    parser.add_argument("--max-icons", type=int, help="Limit icon requests per zoom for a short run")
    parser.add_argument("--image-range", help="Also request every small-image ID in START:END (inclusive)")
    parser.add_argument("--max-files", type=int, help="Limit streamed resources per zoom for a short run")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--skip-maps", action="store_true", help="Skip per-map raw tile packets")
    parser.add_argument("--skip-extra", action="store_true", help="Skip dynamic effects, mobs, flags and named images")
    parser.add_argument("--extra-only", action="store_true", help="Load extra assets into an existing capture")
    parser.add_argument("--effect-range", default="0:300", help="Dynamic effect IDs, inclusive START:END (max 2000 IDs)")
    parser.add_argument("--sprite-names", default="", help="Extra comma-separated image-by-name candidates")
    args = parser.parse_args()
    if not args.server:
        args.server = input("Server (HOST:PORT): ").strip()
    try:
        host, port = parse_address(args.server)
        zooms = sorted({int(z) for z in args.zooms.split(",")})
        if not zooms or any(z not in (1, 2, 3, 4) for z in zooms):
            raise ValueError("Zooms must be a subset of 1,2,3,4")
        if not 1 <= args.batch_size <= 75:
            raise ValueError("Batch size must be 1..75")
        if args.max_icons is not None and args.max_icons < 0:
            raise ValueError("Max icons must be nonnegative")
        if args.max_files is not None and args.max_files < 1:
            raise ValueError("Max files must be positive")
        image_range = None
        effect_start, effect_end = map(int, args.effect_range.split(":"))
        if not 0 <= effect_start <= effect_end <= 32767 or effect_end - effect_start >= 2000:
            raise ValueError("Effect range must contain 1..2000 IDs within 0..32767")
        sprite_names = [value.strip() for value in args.sprite_names.split(",") if value.strip()]
        if len(sprite_names) > 500 or any(not re.fullmatch(r"[\w.-]{1,120}", name, re.ASCII) for name in sprite_names):
            raise ValueError("Invalid sprite names (letters, numbers, underscore, dot and hyphen only)")
        if args.image_range:
            start, end = (int(value) for value in args.image_range.split(":"))
            if start < 0 or end < start or end > 100000:
                raise ValueError("Image range must satisfy 0 <= START <= END <= 100000")
            image_range = range(start, end + 1)
    except ValueError as error:
        parser.error(str(error))
    out = args.out or Path(__file__).resolve().parents[3] / "NRO-clones" / f"{host}-{port}"
    previous_report = out / "report.json"
    if previous_report.is_file():
        try:
            previous_server = json.loads(previous_report.read_text(encoding="utf-8")).get("server")
        except (OSError, ValueError) as error:
            parser.error(f"Cannot read existing report.json: {error}")
        if previous_server and previous_server != args.server:
            parser.error(f"Output folder belongs to {previous_server}; choose a new --out for {args.server}")
    out.mkdir(parents=True, exist_ok=True)
    report = {"server": args.server, "started_utc": datetime.now(timezone.utc).isoformat(),
              "source": "anonymous_client_protocol", "zooms": {}, "game_data": None,
              "updates": {}, "limitations": ["Private server SQL tables and account-only data are not exposed by these public client requests."]}
    def write_report() -> None:
        save(out / "report.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if args.extra_only:
        if not previous_report.is_file():
            parser.error("--extra-only requires an existing report.json")
        report = json.loads(previous_report.read_text(encoding="utf-8"))
    from capture_extra import capture, default_names
    def extra(zoom):
        try:
            value = capture(out, host, port, zoom, args.version, args.timeout,
                            range(effect_start, effect_end + 1), default_names() + sprite_names)
            report.setdefault("extra_assets", {})[str(zoom)] = value
        except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
            report.setdefault("extra_assets", {})[str(zoom)] = {"error": str(error)}
        write_report()

    if args.extra_only:
        for zoom in zooms:
            extra(zoom)
        report["extra_updated_utc"] = datetime.now(timezone.utc).isoformat()
        write_report()
        return

    first = True
    for zoom in zooms:
        print(f"Connecting to {host}:{port}, zoom {zoom}", flush=True)
        row = {}
        report["zooms"][str(zoom)] = row
        try:
            sock, wire, session = connect(host, port, zoom, args.version, args.timeout)
            try:
                row["resource_version"] = session["resource_version"]
                versions = session["image_versions"]
                if first:
                    try:
                        report["game_data"] = get_game_data(wire, out)
                    except (OSError, ValueError, TimeoutError, ConnectionError) as error:
                        report["game_data"] = {"error": str(error)}
                    write_report()
                    try:
                        report["updates"] = get_update_packets(wire, out, (6, 7, 8))
                        report["updates"]["decoded_items"] = decode_items(
                            out / "raw" / "updates", out / "decoded" / "items.json")
                        from extended_data import decode_templates
                        try:
                            report["templates"] = decode_templates(out)
                        except (ValueError, IndexError) as error:
                            report["templates"] = {"error": str(error)}
                    except (OSError, ValueError, TimeoutError, ConnectionError) as error:
                        report["updates"] = {"error": str(error)}
                    write_report()
                    first = False
                try:
                    row["resources"] = get_resources(wire, out, zoom, args.max_files)
                except (OSError, ValueError, TimeoutError, ConnectionError) as error:
                    row["resources"] = {"error": str(error)}
                write_report()
            finally:
                sock.close()
            if zoom == zooms[0] and not args.skip_maps:
                try:
                    report["maps"] = get_maps(host, port, zoom, args.version,
                                              args.timeout, out)
                except (OSError, ValueError, TimeoutError, ConnectionError) as error:
                    report["maps"] = {"error": str(error)}
                write_report()
            if args.icons != "none":
                if args.icons == "all" and versions is not None:
                    ids = [index for index, value in enumerate(versions) if value != 0]
                    row["icon_id_source"] = "server_version_list_nonzero"
                    row["announced_icon_slots"] = len(versions)
                else:
                    ids = referenced_image_ids(out / "decoded")
                    item_file = out / "decoded" / "items.json"
                    if item_file.is_file():
                        ids.update(item["icon_id"] for item in json.loads(
                            item_file.read_text(encoding="utf-8"))["items"] if item["icon_id"] >= 0)
                    ids = sorted(ids)
                    row["icon_id_source"] = "decoded_game_data_references"
                    if args.icons == "all":
                        row["icon_coverage_warning"] = "No server version list received; game-data and item icon IDs requested. Use --image-range for additional IDs."
                if image_range is not None:
                    ids = sorted(set(ids) | set(image_range))
                row["icon_candidates"] = len(ids)
                if args.max_icons is not None:
                    ids = ids[:args.max_icons]
                    row["icon_limited"] = len(ids) < row["icon_candidates"]
                row["icons"] = get_icons(host, port, out, zoom, args.version,
                                          args.timeout, ids, args.batch_size)
                write_report()
        except (OSError, ValueError, TimeoutError, ConnectionError) as error:
            row["error"] = str(error)
        if not args.skip_extra and "error" not in row:
            extra(zoom)
        write_report()
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        from auto_mapping import link
        report["auto_linked_parts"] = link(out)
    except (OSError, ValueError, KeyError, IndexError) as error:
        report["auto_linked_parts"] = {"error": str(error)}
    write_report()
    print(f"Report: {out / 'report.json'}")
    if all("error" in row for row in report["zooms"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
