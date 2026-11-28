"""Local browser UI for clone_server.py; Python standard library only."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from clone_server import parse_address
from auto_mapping import link
from studio_data import catalog, costume, map_detail, mapping_path, part, save_mapping

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parents[2] / "NRO-clones"
TOKEN = secrets.token_urlsafe(24)
LOCK = threading.Lock()
RUN = {"process": None, "state": "idle", "started": None, "ended": None,
       "server": None, "out": None, "exit_code": None, "log": deque(maxlen=500)}


def project_out(payload: dict) -> tuple[str, Path]:
    server = str(payload.get("server", "")).strip()
    custom = str(payload.get("out", "")).strip()
    if custom:
        return server, Path(custom).expanduser().resolve()
    host, port = parse_address(server)
    return server, DEFAULT_OUT / f"{host}-{port}"


def select_project(out: Path, server: str, require_report: bool = False) -> dict:
    report_path = out / "report.json"
    existing = report_path.is_file()
    if require_report and not existing:
        raise ValueError(f"Chưa có report.json trong {out}")
    if existing:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"Không đọc được report.json: {error}") from error
        server = str(report.get("server") or server)
    with LOCK:
        if RUN["process"] is not None and RUN["process"].poll() is None:
            raise RuntimeError("Hãy dừng lượt clone trước khi đổi thư mục")
        if existing:
            link(out)
        RUN.update(process=None, state="loaded" if existing else "idle", started=None, ended=None,
                   server=server, out=str(out), exit_code=None, log=deque(maxlen=500))
    return {"ok": True, "out": str(out), "existing": existing, "server": server}


def snapshot() -> dict:
    with LOCK:
        process = RUN["process"]
        state = RUN["state"]
        if process is not None and state == "running" and process.poll() is not None:
            state = "finished" if process.returncode == 0 else "failed"
            RUN["state"] = state
            RUN["exit_code"] = process.returncode
            RUN["ended"] = time.time()
        out = RUN["out"]
        result = {key: RUN[key] for key in ("state", "started", "ended", "server", "out", "exit_code")}
        result["log"] = list(RUN["log"])
    result["token"] = TOKEN
    result["default_out"] = str(DEFAULT_OUT)
    result["report"] = None
    result["project_exists"] = False
    result["files"] = []
    if out:
        root = Path(out)
        report = root / "report.json"
        if report.is_file() and (result["started"] is None or report.stat().st_mtime >= result["started"] - 1):
            try:
                result["report"] = json.loads(report.read_text(encoding="utf-8"))
                result["project_exists"] = True
            except (OSError, ValueError):
                pass
        decoded = root / "decoded"
        if decoded.is_dir():
            result["files"] = [{"name": path.name, "path": "decoded/" + path.name, "bytes": path.stat().st_size}
                               for path in sorted(decoded.glob("*.json")) if path.is_file()]
        for name in ("costume-parts.json", "mini-pet-parts.json"):
            mapping_file = root / "mappings" / name
            if mapping_file.is_file():
                result["files"].append({"name": name, "path": "mappings/" + name,
                                        "bytes": mapping_file.stat().st_size})
    return result


def validate(config: dict) -> tuple[str, Path, list[str]]:
    server = str(config.get("server", "")).strip()
    host, port = parse_address(server)
    zooms = config.get("zooms")
    if not isinstance(zooms, list) or not zooms or any(type(z) is not int or z not in (1, 2, 3, 4) for z in zooms):
        raise ValueError("Chọn ít nhất một mức zoom 1–4")
    icons = config.get("icons", "all")
    if icons not in ("all", "referenced", "none"):
        raise ValueError("Chế độ ảnh không hợp lệ")
    custom_out = str(config.get("out", "")).strip()
    out = Path(custom_out).expanduser().resolve() if custom_out else DEFAULT_OUT / f"{host}-{port}"
    command = [sys.executable, "-u", str(HERE / "clone_server.py"),
               "--server", server, "--out", str(out), "--zooms", ",".join(map(str, sorted(set(zooms)))),
               "--icons", icons]
    if config.get("skip_maps") is True:
        command.append("--skip-maps")
    for key, flag, minimum in (("max_icons", "--max-icons", 0), ("max_files", "--max-files", 1)):
        raw = config.get(key)
        if raw not in (None, ""):
            value = int(raw)
            if value < minimum:
                raise ValueError(f"{key} phải >= {minimum}")
            command.extend((flag, str(value)))
    image_range = str(config.get("image_range", "")).strip()
    if image_range:
        pieces = image_range.split(":")
        if len(pieces) != 2 or not all(piece.isdigit() for piece in pieces):
            raise ValueError("Dải ảnh phải là START:END")
        start, end = map(int, pieces)
        if start > end or end > 100000:
            raise ValueError("Dải ảnh phải thỏa START <= END <= 100000")
        command.extend(("--image-range", image_range))
    return server, out, command


def follow(process: subprocess.Popen) -> None:
    try:
        assert process.stdout is not None
        for line in process.stdout:
            with LOCK:
                RUN["log"].append(line.rstrip("\r\n"))
        code = process.wait()
    except Exception as error:
        code = -1
        with LOCK:
            RUN["log"].append(f"UI reader error: {error}")
    with LOCK:
        if RUN["process"] is process:
            RUN["state"] = "stopped" if RUN["state"] == "stopping" else ("finished" if code == 0 else "failed")
            RUN["exit_code"] = code
            RUN["ended"] = time.time()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, status: int, value: dict) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/":
            data = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/studio.js":
            data = (HERE / "studio.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/api/status":
            self.send_json(200, snapshot())
        elif parsed.path == "/api/download":
            with LOCK:
                out = RUN["out"]
            name = parse_qs(parsed.query).get("file", [""])[0]
            allowed = {"report.json", "decoded/part.json", "decoded/dart.json", "decoded/arrow.json",
                       "decoded/effect.json", "decoded/image.json", "decoded/skill.json",
                       "decoded/items.json", "decoded/map-names.json", "mappings/costume-parts.json",
                       "mappings/mini-pet-parts.json"}
            if not out or name not in allowed:
                self.send_error(404)
                return
            target = Path(out) / name
            if not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif parsed.path == "/api/preview":
            with LOCK:
                out = RUN["out"]
            params = parse_qs(parsed.query)
            name = params.get("file", [""])[0]
            query = params.get("query", [""])[0].strip().casefold()[:100]
            allowed = {"part.json", "dart.json", "arrow.json", "effect.json",
                       "image.json", "skill.json", "items.json", "map-names.json"}
            if not out or name not in allowed:
                self.send_json(404, {"error": "File không hợp lệ"})
                return
            target = Path(out) / "decoded" / name
            if not target.is_file():
                self.send_json(404, {"error": "Chưa có file giải mã"})
                return
            try:
                values = json.loads(target.read_text(encoding="utf-8"))
                if name == "items.json":
                    values = values.get("items", [])
                matches = []
                for index, value in enumerate(values):
                    item_id = value.get("id", value.get("index", index)) if isinstance(value, dict) else index
                    item_name = value.get("name", "") if isinstance(value, dict) else str(value)
                    if query and query not in str(item_id).casefold() and query not in str(item_name).casefold():
                        continue
                    matches.append(value if isinstance(value, dict) else {"id": index, "name": value})
                    if len(matches) >= 40:
                        break
                self.send_json(200, {"records": matches, "shown": len(matches), "limited": len(matches) == 40})
            except (OSError, ValueError, TypeError) as error:
                self.send_json(500, {"error": str(error)})
        elif parsed.path in ("/api/catalog", "/api/part", "/api/costume", "/api/map", "/api/poses", "/api/asset"):
            if parsed.path == "/api/poses":
                self.send_json(200, json.loads((HERE / "char-poses.json").read_text(encoding="utf-8")))
                return
            with LOCK:
                out = RUN["out"]
            if not out:
                self.send_json(400, {"error": "Hãy clone hoặc mở bản lưu trước"})
                return
            params = parse_qs(parsed.query)
            root = Path(out)
            try:
                if parsed.path == "/api/catalog":
                    result = catalog(root, params.get("kind", [""])[0], params.get("query", [""])[0],
                                     offset=int(params.get("offset", ["0"])[0]),
                                     category=params.get("category", ["featured"])[0])
                elif parsed.path == "/api/part":
                    result = part(root, int(params.get("id", ["-1"])[0]))
                elif parsed.path == "/api/costume":
                    result = costume(root, int(params.get("id", ["-1"])[0]))
                elif parsed.path == "/api/map":
                    result = map_detail(root, int(params.get("id", ["-1"])[0]))
                else:
                    zoom = int(params.get("zoom", ["0"])[0])
                    image_id = int(params.get("id", ["-1"])[0])
                    if zoom not in (1, 2, 3, 4) or not 0 <= image_id <= 100000:
                        raise ValueError("Image ID hoặc zoom không hợp lệ")
                    image_path = root / "icons" / f"zoom{zoom}" / f"{image_id}.png"
                    if not image_path.is_file():
                        self.send_error(404)
                        return
                    data = image_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Cache-Control", "public, max-age=60")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_json(200, result)
            except (OSError, ValueError, TypeError, KeyError) as error:
                self.send_json(400, {"error": str(error)})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.headers.get("X-Clone-Token") != TOKEN:
            self.send_json(403, {"error": "Invalid UI token"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 16384:
                raise ValueError("Request quá lớn")
            payload = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(payload, dict):
                raise ValueError("Request không hợp lệ")
            if self.path == "/api/start":
                server, out = project_out(payload)
                if (out / "report.json").is_file() and payload.get("force") is not True:
                    self.send_json(200, {**select_project(out, server, require_report=True), "reused": True})
                    return
                server, out, command = validate(payload)
                with LOCK:
                    if RUN["process"] is not None and RUN["process"].poll() is None:
                        self.send_json(409, {"error": "Đang có một lượt clone chạy"})
                        return
                    process = subprocess.Popen(command, cwd=HERE.parents[1], stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                               errors="replace", bufsize=1)
                    RUN.update(process=process, state="running", started=time.time(), ended=None,
                               server=server, out=str(out), exit_code=None, log=deque(maxlen=500))
                threading.Thread(target=follow, args=(process,), daemon=True).start()
                self.send_json(200, {"ok": True, "out": str(out)})
            elif self.path == "/api/stop":
                with LOCK:
                    process = RUN["process"]
                    if process is not None and process.poll() is None:
                        RUN["state"] = "stopping"
                        process.terminate()
                self.send_json(200, {"ok": True})
            elif self.path == "/api/load":
                server, out = project_out(payload)
                self.send_json(200, select_project(out, server, require_report=True))
            elif self.path == "/api/select-folder":
                server, out = project_out(payload)
                self.send_json(200, select_project(out, server))
            elif self.path == "/api/choose-folder":
                initial = str(payload.get("initial", "")).strip() or str(DEFAULT_OUT)
                result = subprocess.run([sys.executable, str(HERE / "choose_folder.py"), initial],
                                        capture_output=True, text=True, encoding="utf-8",
                                        errors="replace", timeout=600, check=False)
                if result.returncode != 0:
                    raise ValueError(result.stderr.strip() or "Không mở được hộp thoại chọn thư mục")
                if result.stdout.strip():
                    selected = select_project(Path(result.stdout.strip()), str(payload.get("server", "")).strip())
                    self.send_json(200, {"path": result.stdout.strip(), **selected})
                else:
                    self.send_json(200, {"path": "", "cancelled": True})
            elif self.path == "/api/mapping":
                with LOCK:
                    out = RUN["out"]
                if not out:
                    raise ValueError("Hãy clone hoặc mở bản lưu trước")
                item_id = int(payload.get("item_id", -1))
                selected = payload.get("mapping")
                if not isinstance(selected, dict):
                    raise ValueError("Mapping không hợp lệ")
                result = save_mapping(Path(out), item_id, selected)
                item_type = costume(Path(out), item_id)["type"]
                self.send_json(200, {"mapping": result, "path": str(mapping_path(Path(out), item_type))})
            else:
                self.send_error(404)
        except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8183)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Clone Studio: {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        with LOCK:
            process = RUN["process"]
            if process is not None and process.poll() is None:
                process.terminate()


if __name__ == "__main__":
    main()
