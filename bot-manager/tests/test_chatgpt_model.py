"""Contract checks for the official ChatGPT plan integration."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from ai import chatgpt_model


class ChatGPTModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_patch = patch.object(chatgpt_model, "STATE", Path(self.temp.name) / "state.json")
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.model = chatgpt_model.ChatGPTModel()

    def test_sign_in_uses_dynamic_registration_and_pkce(self):
        url = self.model.start_sign_in("http://127.0.0.1:8765/auth/chatgpt/callback")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["client_id"], ["dynamic_agent_client"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertIn("chatgpt.tokens.use.direct", query["scope"][0])
        self.assertTrue(query["ext_agent_host_id"][0].startswith("urn:uuid:"))
        self.assertNotIn("access_token", url)

    def test_large_tokens_are_encrypted_on_disk(self):
        from cryptography.fernet import Fernet
        self.model._state["active"] = "client"
        record = {"access_token": "a" * 4000, "refresh_token": "r" * 4000}
        key = Fernet.generate_key()
        with patch.object(self.model, "_vault_key", return_value=key):
            self.model._store_credentials("client", record)
            path = self.model._credential_path("client")
            self.assertNotIn(b"aaaa", path.read_bytes())
            self.assertEqual(self.model._credentials(), record)

    def test_decision_uses_responses_stream_and_rejects_unlisted_action(self):
        self.model._state["active"] = "client"
        self.model._state["accounts"]["client"] = {"model": "example-sol"}
        events = (b'data: {"type":"response.output_text.delta","delta":"{\\"choice\\":\\"none\\",\\"reason\\":\\"OK\\"}"}\n\n'
                  b'data: {"type":"response.completed"}\n\n')
        with patch.object(self.model, "_access_token", return_value="test-token"), patch.object(
            chatgpt_model.urllib.request, "urlopen", return_value=io.BytesIO(events)
        ) as open_mock:
            result = self.model.decide({}, [{"id": "none", "description": "continue"}])
        self.assertEqual(result["choice"], "none")
        request = open_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        body = json.loads(request.data)
        self.assertIs(body["store"], False)
        self.assertIs(body["stream"], True)
        self.assertNotIn("temperature", body)

        bad = b'data: {"type":"response.output_text.delta","delta":"{\\"choice\\":\\"buy:999\\"}"}\n\ndata: {"type":"response.completed"}\n\n'
        with patch.object(self.model, "_access_token", return_value="test-token"), patch.object(
            chatgpt_model.urllib.request, "urlopen", return_value=io.BytesIO(bad)
        ):
            with self.assertRaises(ValueError):
                self.model.decide({}, [{"id": "none"}])


if __name__ == "__main__":
    unittest.main()
