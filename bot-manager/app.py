"""Local web dashboard for headless NRO test bots. Python standard library only."""

from __future__ import annotations

import argparse
import json
import random
import re
import threading
import webbrowser
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bot import BotConfig, BotManager, human_nickname
from ai.chatgpt_model import CHATGPT_MODEL

ROOT = Path(__file__).resolve().parent
MANAGER = BotManager()


class LocalServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR can let two dashboards bind the same port.
    allow_reuse_address = False


def valid_config(raw: dict) -> BotConfig:
    name = str(raw.get("name", "")).strip()
    username = str(raw.get("username", "")).strip()
    password = str(raw.get("password", ""))
    host = str(raw.get("host", "127.0.0.1")).strip()
    if not 1 <= len(name) <= 40:
        raise ValueError("Tên bot phải có 1–40 ký tự")
    if not 1 <= len(username) <= 64 or not re.fullmatch(r"[A-Za-z0-9_.@-]+", username):
        raise ValueError("Tài khoản phải có 1–64 ký tự ASCII hợp lệ")
    if not 1 <= len(password) <= 128:
        raise ValueError("Cần nhập mật khẩu tài khoản")
    if not host or len(host) > 255 or re.search(r"[\s/\\]", host):
        raise ValueError("Địa chỉ server không hợp lệ")
    try:
        port = int(raw.get("port", 14445))
        gender = int(raw.get("gender", 0))
        heal_item = int(raw.get("heal_item") or 0)
        shop_map = int(raw.get("shop_map") if raw.get("shop_map") not in (None, "") else -1)
        shop_npc = int(raw.get("shop_npc") or -1)
        shop_menu = int(raw.get("shop_menu") or 0)
        shop_item = int(raw.get("shop_item") or 0)
        shop_min = int(raw.get("shop_min") or 0)
        shop_target = int(raw.get("shop_target") or 0)
        trade_partner = int(raw.get("trade_partner") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("ID và số lượng phải là số nguyên") from exc
    if not 1 <= port <= 65535 or gender not in (0, 1, 2) or any(value < 0 for value in (heal_item, shop_menu, shop_item, shop_min, shop_target, trade_partner)) or shop_map < -1:
        raise ValueError("Cổng hoặc ID không hợp lệ")
    if shop_item and (shop_npc < 0 or shop_min < 1 or shop_target <= shop_min):
        raise ValueError("Mua đồ cần NPC, ngưỡng tối thiểu và số lượng mục tiêu lớn hơn ngưỡng")
    mode = str(raw.get("mode", "auto"))
    stat = str(raw.get("stat", "balanced"))
    auto_register = raw.get("auto_register", True)
    if auto_register not in (True, False):
        raise ValueError("Tùy chọn tự tạo tài khoản không hợp lệ")
    if auto_register and not 4 <= len(username) <= 18:
        raise ValueError("Tự tạo tài khoản yêu cầu tên đăng nhập 4–18 ký tự")
    if auto_register and not 5 <= len(password) <= 18:
        raise ValueError("Tự tạo tài khoản yêu cầu mật khẩu 5–18 ký tự")
    if mode not in ("auto", "farm", "ai") or stat not in ("balanced", "attack", "hp", "mp", "def", "off"):
        raise ValueError("Chế độ bot hoặc cộng chỉ số không hợp lệ")
    return BotConfig(name, username, password, host, port, mode, stat,
                     heal_item, shop_map, shop_npc, shop_menu, shop_item, shop_min,
                     shop_target, trade_partner, auto_register, gender)


def valid_batch(raw: dict) -> list[BotConfig]:
    try:
        count = int(raw.get("count", 1))
        start_number = int(raw.get("start_number", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Số lượng và số bắt đầu phải là số nguyên") from exc
    if not 1 <= count <= BotManager.MAX_BOTS or not 0 <= start_number <= 999999:
        raise ValueError(f"Số lượng phải từ 1–{BotManager.MAX_BOTS}; số bắt đầu từ 0–999999")
    username_prefix = str(raw.get("username_prefix", "")).strip()
    configs = []
    nicknames = set()
    for number in range(start_number, start_number + count):
        gender = raw.get("gender", 0)
        if gender == "random":
            gender = random.choice((0, 1, 2))
        username = f"{username_prefix}{number}"
        seed = username
        name = human_nickname(seed)
        while name.casefold() in nicknames:
            seed += "_"
            name = human_nickname(seed)
        nicknames.add(name.casefold())
        entry = dict(raw, name=name, username=username, gender=gender)
        configs.append(valid_config(entry))
    return configs


def valid_config_update(current: BotConfig, raw: dict) -> BotConfig:
    allowed = {"mode", "stat", "gender", "heal_item", "shop_map", "shop_npc", "shop_menu",
               "shop_item", "shop_min", "shop_target", "trade_partner"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError("Trường cấu hình không hợp lệ: " + ", ".join(sorted(unknown)))
    merged = asdict(current)
    merged.update(raw)
    return valid_config(merged)


class Handler(BaseHTTPRequestHandler):
    server_version = "NroBotManager/1.0"

    def log_message(self, fmt: str, *args) -> None:
        # Credentials and request bodies never go to console logs.
        if not self.path.startswith(("/api/bots", "/api/ai", "/auth/chatgpt/callback")):
            super().log_message(fmt, *args)

    def _json(self, status: int, data: dict | list) -> None:
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _body(self) -> dict:
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise ValueError("Yêu cầu phải là JSON")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 8192:
            raise ValueError("Kích thước yêu cầu không hợp lệ")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Dữ liệu phải là đối tượng JSON")
        return data

    def _parts(self) -> list[str]:
        return [part for part in urlparse(self.path).path.split("/") if part]

    def do_GET(self) -> None:
        try:
            parts = self._parts()
            if parts == ["auth", "chatgpt", "callback"]:
                try:
                    CHATGPT_MODEL.finish_sign_in(parse_qs(urlparse(self.path).query))
                    message = "Đã kết nối ChatGPT. Quay lại Bot Manager để chọn model."
                except Exception as exc:
                    message = "Kết nối ChatGPT thất bại: " + str(exc)
                import html
                content = ("<!doctype html><html lang='vi'><meta charset='utf-8'>"
                           "<title>Kết nối ChatGPT</title><body><h2>" + html.escape(message) +
                           "</h2><a href='/'>Quay lại Bot Manager</a></body></html>").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif parts == ["api", "ai", "status"]:
                self._json(200, CHATGPT_MODEL.status())
            elif parts == ["api", "ai", "models"]:
                self._json(200, CHATGPT_MODEL.models())
            elif len(parts) == 3 and parts[:2] == ["assets", "icon"] and re.fullmatch(r"\d+\.png", parts[2]):
                icon_id = int(parts[2][:-4])
                image = ROOT.parent / "Server" / "resources" / "normal" / "image" / "3" / "icon" / f"{icon_id}.png"
                if not image.is_file():
                    self._json(404, {"error": "Không tìm thấy hình vật phẩm"})
                    return
                content = image.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif parts == ["api", "bots"]:
                self._json(200, MANAGER.all())
            elif len(parts) == 3 and parts[:2] == ["api", "bots"]:
                self._json(200, MANAGER.get(parts[2]).snapshot(include_logs=True))
            elif parts == ["api", "health"]:
                self._json(200, {"ok": True})
            elif parts in ([], ["index.html"]):
                content = (ROOT / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif parts in (["style.css"], ["app.js"]):
                content = (ROOT / parts[0]).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8" if parts[0].endswith(".css") else "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._json(404, {"error": "Không tìm thấy"})
        except KeyError:
            self._json(404, {"error": "Bot không tồn tại"})
        except RuntimeError as exc:
            self._json(400, {"error": str(exc)})

    def do_POST(self) -> None:
        try:
            parts = self._parts()
            if parts == ["api", "ai", "sign-in"]:
                payload = self._body()
                callback = f"http://127.0.0.1:{self.server.server_address[1]}/auth/chatgpt/callback"
                url = CHATGPT_MODEL.start_sign_in(callback, new_account=payload.get("new_account") is True)
                self._json(200, {"url": url})
            elif parts == ["api", "ai", "provider"]:
                CHATGPT_MODEL.set_provider(str(self._body().get("provider", "")))
                self._json(200, CHATGPT_MODEL.status())
            elif parts == ["api", "ai", "model"]:
                CHATGPT_MODEL.select_model(str(self._body().get("model", "")))
                self._json(200, CHATGPT_MODEL.status())
            elif parts == ["api", "ai", "research"]:
                self._body()
                self._json(200, {"research": CHATGPT_MODEL.research()})
            elif parts == ["api", "bots", "start-all"]:
                bots = MANAGER.all()
                candidates = [MANAGER.get(item["id"]) for item in bots
                              if item["status"] not in ("running", "connecting", "reconnecting")]
                MANAGER.start_many(candidates)
                self._json(200, {"ok": True, "count": len(candidates)})
            elif parts == ["api", "bots", "delete-all"]:
                self._json(200, {"ok": True, "count": MANAGER.remove_all()})
            elif parts == ["api", "bots", "stop-all"]:
                bots = MANAGER.all()
                for item in bots:
                    if item["status"] not in ("stopped", "disconnected", "error"):
                        MANAGER.get(item["id"]).stop()
                self._json(200, {"ok": True, "count": len(bots)})
            elif parts == ["api", "bots"]:
                bot = MANAGER.create(valid_config(self._body()))
                bot.start()
                self._json(201, bot.snapshot(include_logs=True))
            elif parts == ["api", "bots", "batch"]:
                bots = MANAGER.create_many(valid_batch(self._body()))
                MANAGER.start_many(bots)
                self._json(201, [bot.snapshot() for bot in bots])
            elif len(parts) == 4 and parts[:2] == ["api", "bots"]:
                bot = MANAGER.get(parts[2])
                if parts[3] == "start":
                    bot.start()
                elif parts[3] == "stop":
                    bot.stop()
                elif parts[3] == "trade":
                    bot.invite_trade()
                elif parts[3] == "item":
                    payload = self._body()
                    try:
                        item_id = int(payload.get("item_id", -1))
                    except (TypeError, ValueError) as exc:
                        raise ValueError("ID vật phẩm không hợp lệ") from exc
                    if item_id < 0:
                        raise ValueError("ID vật phẩm không hợp lệ")
                    bot.item_action(str(payload.get("action", "")), str(payload.get("location", "")), item_id)
                elif parts[3] == "box":
                    bot.request_box()
                elif parts[3] == "skip-quest":
                    bot.request_skip_quest()
                    if bot.config.mode == "farm":
                        bot = MANAGER.update_config(parts[2], replace(bot.config, mode="auto"))
                elif parts[3] == "config":
                    bot = MANAGER.update_config(parts[2], valid_config_update(bot.config, self._body()))
                else:
                    self._json(404, {"error": "Không tìm thấy"})
                    return
                self._json(200, bot.snapshot(include_logs=True))
            else:
                self._json(404, {"error": "Không tìm thấy"})
        except KeyError:
            self._json(404, {"error": "Bot không tồn tại"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except (OSError, RuntimeError) as exc:
            self._json(500, {"error": "Không lưu được cấu hình bot: " + str(exc)})

    def do_DELETE(self) -> None:
        parts = self._parts()
        if len(parts) != 3 or parts[:2] != ["api", "bots"]:
            self._json(404, {"error": "Không tìm thấy"})
            return
        try:
            MANAGER.remove(parts[2])
            self._json(200, {"ok": True})
        except KeyError:
            self._json(404, {"error": "Bot không tồn tại"})
        except (OSError, RuntimeError) as exc:
            self._json(500, {"error": "Không lưu được cấu hình bot: " + str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="NRO local bot manager")
    parser.add_argument("--port", type=int, default=8765, help="Local dashboard port (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1-65535")
    try:
        server = LocalServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        parser.exit(1, f"Không mở được cổng {args.port}; Bot Manager có thể đang chạy: {exc}\n")
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Bot manager: {url}")
    print("Press Ctrl+C to stop all bots and close the dashboard.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        MANAGER.close()


if __name__ == "__main__":
    main()
