"""Official Sign in with ChatGPT plan usage for this local, open-source bot."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

STATE = Path(__file__).resolve().parent / "state" / "chatgpt.json"
KEYRING_SERVICE = "NroBotManager-ChatGPT"
KEYRING_VAULT_KEY = "token-vault-key"
AUTH = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="NroChatGPT")


def _dependencies():
    try:
        import jwt
        import keyring
    except ImportError as exc:
        raise RuntimeError("Cài kết nối ChatGPT: python -m pip install -r ai/requirements-chatgpt.txt") from exc
    return jwt, keyring


def _request_json(url: str, *, data: dict | None = None, token: str | None = None,
                  timeout: int = 30) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ChatGPT HTTP {exc.code}; kiểm tra quyền kết nối hoặc đăng nhập lại") from exc


class ChatGPTModel:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pending: dict | None = None
        self._state = {"provider": "chatgpt", "host_id": "", "active": "", "accounts": {}}
        if STATE.exists():
            self._state.update(json.loads(STATE.read_text(encoding="utf-8")))
        self._state["provider"] = "chatgpt"

    def _save(self) -> None:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        temp = STATE.with_suffix(".tmp")
        temp.write_text(json.dumps(self._state, ensure_ascii=False), encoding="utf-8")
        temp.replace(STATE)

    def status(self) -> dict:
        with self._lock:
            active = self._state["active"]
            account = self._state["accounts"].get(active, {})
            return {"provider": self._state["provider"], "connected": bool(active and account),
                    "email": account.get("email", ""), "model": account.get("model", ""),
                    "research": self._state.get("research", {}).get("text", ""),
                    "accounts": [{"client_id": client, "email": info.get("email", ""),
                                  "active": client == active} for client, info in self._state["accounts"].items()]}

    def set_provider(self, provider: str) -> None:
        if provider != "chatgpt":
            raise ValueError("Nguồn AI không hợp lệ")
        with self._lock:
            self._credentials()
            self._state["provider"] = provider
            self._save()

    def _credentials(self) -> dict:
        active = self._state["active"]
        if not active:
            raise RuntimeError("Chưa kết nối ChatGPT")
        path = self._credential_path(active)
        if not path.exists():
            raise RuntimeError("Phiên ChatGPT đã mất; hãy đăng nhập lại")
        try:
            from cryptography.fernet import Fernet
            raw = Fernet(self._vault_key()).decrypt(path.read_bytes())
            return json.loads(raw)
        except Exception as exc:
            raise RuntimeError("Không đọc được phiên ChatGPT; hãy đăng nhập lại") from exc

    @staticmethod
    def _credential_path(client_id: str) -> Path:
        digest = hashlib.sha256(client_id.encode("utf-8")).hexdigest()
        return STATE.parent / f"credential-{digest}.bin"

    @staticmethod
    def _vault_key() -> bytes:
        _, keyring = _dependencies()
        value = keyring.get_password(KEYRING_SERVICE, KEYRING_VAULT_KEY)
        if not value:
            from cryptography.fernet import Fernet
            value = Fernet.generate_key().decode("ascii")
            keyring.set_password(KEYRING_SERVICE, KEYRING_VAULT_KEY, value)
        return value.encode("ascii")

    def _store_credentials(self, client_id: str, record: dict) -> None:
        from cryptography.fernet import Fernet
        path = self._credential_path(client_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = Fernet(self._vault_key()).encrypt(json.dumps(record).encode("utf-8"))
        temp = path.with_suffix(".tmp")
        temp.write_bytes(encrypted)
        temp.replace(path)

    def start_sign_in(self, redirect_uri: str, *, new_account: bool = False) -> str:
        _dependencies()
        with self._lock:
            if not self._state["host_id"]:
                self._state["host_id"] = "urn:uuid:" + str(uuid.uuid4())
                self._save()
            active = self._state["active"] if not new_account else ""
            account = self._state["accounts"].get(active, {})
            verifier = secrets.token_urlsafe(48)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            pending = {"state": secrets.token_urlsafe(32), "nonce": secrets.token_urlsafe(32),
                       "verifier": verifier, "redirect_uri": redirect_uri, "client_id": active,
                       "expires": time.time() + 600}
            self._pending = pending
            args = {"client_id": active or "dynamic_agent_client", "response_type": "code",
                    "redirect_uri": redirect_uri, "scope": SCOPES, "resource": RESOURCE,
                    "state": pending["state"], "nonce": pending["nonce"],
                    "code_challenge_method": "S256", "code_challenge": challenge,
                    "ext_agent_host_id": self._state["host_id"]}
            if active:
                if account.get("email"):
                    args["login_hint"] = account["email"]
            else:
                args["agent_name_hint"] = "NRO Bot Manager"
            return AUTH + "/api/accounts/authorize?" + urllib.parse.urlencode(args)

    def finish_sign_in(self, query: dict[str, list[str]]) -> None:
        jwt, _ = _dependencies()
        with self._lock:
            pending, self._pending = self._pending, None
            if (not pending or time.time() >= pending["expires"]
                    or not secrets.compare_digest(query.get("state", [""])[0], pending["state"])):
                raise ValueError("Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
            if query.get("error"):
                raise ValueError("Bạn chưa cấp quyền dùng gói ChatGPT")
            code = query.get("code", [""])[0]
            issued = query.get("client_id", [pending["client_id"]])[0]
            if not code or not issued or (pending["client_id"] and issued != pending["client_id"]):
                raise ValueError("ChatGPT chưa trả mã đăng nhập hợp lệ")
            tokens = _request_json(AUTH + "/api/accounts/oauth/token", data={
                "grant_type": "authorization_code", "client_id": issued, "code": code,
                "code_verifier": pending["verifier"], "redirect_uri": pending["redirect_uri"],
                "resource": RESOURCE})
            scopes = tokens.get("scope", "").split()
            if "chatgpt.tokens.use.direct" not in scopes:
                raise ValueError("Tài khoản chưa cấp quyền dùng gói ChatGPT cho bot")
            id_token = tokens.get("id_token", "")
            if not id_token or not tokens.get("access_token") or not tokens.get("refresh_token"):
                raise ValueError("ChatGPT chưa trả đủ thông tin phiên")
            jwks = jwt.PyJWKClient(AUTH + "/.well-known/jwks.json")
            signing_key = jwks.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(id_token, signing_key.key, algorithms=[signing_key.algorithm_name], audience=issued,
                                issuer=AUTH, leeway=5, options={"require": ["sub", "exp", "iat"]})
            if claims.get("nonce") != pending["nonce"] or not claims.get("sub"):
                raise ValueError("ChatGPT trả danh tính không khớp")
            old = self._state["accounts"].get(issued, {})
            if old.get("subject") and old["subject"] != claims["sub"]:
                raise ValueError("Tài khoản ChatGPT không khớp lần đăng nhập trước")
            record = {"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
                      "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
                      "id_token": id_token, "scopes": scopes}
            self._store_credentials(issued, record)
            self._state["accounts"][issued] = {"subject": claims["sub"],
                                                 "email": claims.get("email", ""),
                                                 "model": old.get("model", "")}
            self._state["active"] = issued
            self._save()

    def _access_token(self) -> str:
        with self._lock:
            record = self._credentials()
            if time.time() < record["expires_at"] - 120:
                return record["access_token"]
            active = self._state["active"]
            updated = _request_json(AUTH + "/api/accounts/oauth/token", data={
                "grant_type": "refresh_token", "client_id": active,
                "refresh_token": record["refresh_token"], "resource": RESOURCE})
            if not updated.get("access_token") or not updated.get("refresh_token"):
                raise RuntimeError("Không gia hạn được phiên ChatGPT; hãy đăng nhập lại")
            record.update(access_token=updated["access_token"], refresh_token=updated["refresh_token"],
                          expires_at=time.time() + int(updated.get("expires_in", 3600)))
            self._store_credentials(active, record)
            return record["access_token"]

    def models(self) -> list[dict]:
        data = _request_json(RESOURCE + "/models", token=self._access_token())
        return [{"slug": model["slug"], "name": model.get("display_name", model["slug"])}
                for model in data.get("models", []) if model.get("visibility") == "list" and model.get("slug")]

    def select_model(self, slug: str) -> None:
        available = {model["slug"] for model in self.models()}
        if slug not in available:
            raise ValueError("Model không có trong tài khoản ChatGPT này")
        with self._lock:
            self._state["accounts"][self._state["active"]]["model"] = slug
            self._save()

    def decide(self, observation: dict, choices: list[dict]) -> dict:
        with self._lock:
            model = self._state["accounts"].get(self._state["active"], {}).get("model", "")
        if not model:
            available = self.models()
            if not available:
                raise RuntimeError("Tài khoản ChatGPT chưa có model khả dụng")
            preferred = next((entry for entry in available if entry["slug"].endswith("-sol")), available[0])
            model = preferred["slug"]
            self.select_model(model)
        allowed = {entry["id"] for entry in choices}
        payload = {"model": model, "store": False, "stream": True,
                   "instructions": "Bạn chọn 1 hành động cho bot game Ngọc Rồng từ choices. Ưu tiên sống sót, tăng sức mạnh, nhiệm vụ và trang bị phù hợp. Chỉ trả JSON gồm choice là ID có sẵn và reason ngắn. Không bịa ID. Kiến thức tham khảo: " + self._state.get("research", {}).get("text", "")[:1200],
                   "input": [{"role": "user", "content": json.dumps({"observation": observation,
                                                                        "choices": choices}, ensure_ascii=False)}]}
        raw = self._stream(payload)
        if raw.startswith("```"):
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        decision = json.loads(raw)
        if not isinstance(decision, dict) or decision.get("choice") not in allowed:
            raise ValueError("ChatGPT trả hành động ngoài danh sách cho phép")
        return {"choice": decision["choice"], "reason": str(decision.get("reason", ""))[:160]}

    def research(self) -> str:
        with self._lock:
            model = self._state["accounts"].get(self._state["active"], {}).get("model", "")
        if not model:
            raise ValueError("Hãy chọn model ChatGPT trước")
        payload = {"model": model, "store": False, "stream": True,
                   "tools": [{"type": "web_search"}],
                   "instructions": "Tìm tài liệu công khai về Ngọc Rồng Online. Ưu tiên ngocrongonline.com và nguồn đáng tin. Viết tối đa 1000 ký tự tiếng Việt về chiến lược lên sức mạnh, cộng chỉ số, trang bị, sách kỹ năng và nhiệm vụ cho bot. Không nêu ID map/quái/vật phẩm nếu không chắc. Đây là game thử nghiệm có thể khác bản công khai.",
                   "input": [{"role": "user", "content": "Tìm hiểu cách chơi Ngọc Rồng Online để điều khiển bot tiến bộ hiệu quả."}]}
        result = self._stream(payload)[:1200]
        if not result:
            raise RuntimeError("ChatGPT chưa trả kiến thức game")
        with self._lock:
            self._state["research"] = {"text": result, "at": time.time()}
            self._save()
        return result

    def _stream(self, payload: dict) -> str:
        request = urllib.request.Request(RESOURCE + "/responses",
                                         data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer " + self._access_token()}, method="POST")
        chunks: list[str] = []
        completed = False
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                for line in response:
                    if not line.startswith(b"data: "):
                        continue
                    if line[6:].strip() == b"[DONE]":
                        continue
                    event = json.loads(line[6:])
                    if event.get("type") == "response.output_text.delta":
                        chunks.append(event.get("delta", ""))
                    elif event.get("type") == "response.completed":
                        completed = True
                        if not chunks:
                            for item in event.get("response", {}).get("output", []):
                                chunks.extend(part.get("text", "") for part in item.get("content", [])
                                              if part.get("type") == "output_text")
                    elif event.get("type") in ("response.failed", "response.incomplete"):
                        error = event.get("response", {}).get("error") or {}
                        raise RuntimeError("ChatGPT chưa hoàn thành: " + str(error.get("code", "unknown")))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"ChatGPT HTTP {exc.code}; kiểm tra giới hạn gói hoặc đăng nhập lại") from exc
        if not completed:
            raise RuntimeError("ChatGPT ngắt kết nối trước khi hoàn thành")
        return "".join(chunks).strip()


CHATGPT_MODEL = ChatGPTModel()
