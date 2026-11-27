"""Regressions for the console languages."""
import http.client
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from web import messages
from web import server

ROOT = Path(__file__).resolve().parents[1]
DATA_I18N = re.compile(r'data-i18n(?:-[a-z-]+)?="([^"]+)"')
CALL = re.compile(r'\bt\("([^"]+)"')


class CatalogueTests(unittest.TestCase):
    def test_every_key_exists_in_both_languages(self):
        for key, entry in messages.MESSAGES.items():
            self.assertIn("en", entry, key)
            self.assertIn("zh-CN", entry, key)
            self.assertTrue(entry["zh-CN"].strip(), key)
            # A key that only carries a separator may have an empty English text.
            self.assertTrue((entry["en"] + entry["zh-CN"]).strip(), key)

    def test_every_marked_element_has_a_known_key(self):
        html = (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
        keys = set(DATA_I18N.findall(html))
        self.assertGreater(len(keys), 150)
        unknown = sorted(key for key in keys if key not in messages.MESSAGES)
        self.assertEqual(unknown, [])

    def test_every_translated_call_has_a_known_key(self):
        script = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        keys = set(CALL.findall(script))
        self.assertGreater(len(keys), 200)
        unknown = sorted(key for key in keys if key not in messages.MESSAGES)
        self.assertEqual(unknown, [])

    def test_the_language_of_a_request_is_normalized(self):
        self.assertEqual(messages.normalize_language("zh"), "zh-CN")
        self.assertEqual(messages.normalize_language("zh-Hans"), "zh-CN")
        self.assertEqual(messages.normalize_language("en-GB"), "en")
        self.assertEqual(messages.normalize_language(""), messages.DEFAULT_LANGUAGE)

    def test_a_message_is_localized_by_its_key_and_by_its_text(self):
        self.assertEqual(messages.message("setup-title", "en"), "Connect your HTTP proxy")
        self.assertEqual(messages.message("setup-title", "zh-CN"), "连接你的 HTTP 代理")
        self.assertEqual(messages.localize("网关不存在", "en"), "The gateway does not exist")
        self.assertEqual(messages.localize("网关不存在", "zh-CN"), "网关不存在")
        self.assertEqual(messages.localize("a sentence nobody translated", "en"),
                         "a sentence nobody translated")

    def test_the_catalogue_script_carries_every_message(self):
        script = messages.catalogue_script()
        self.assertTrue(script.startswith("window.NPT_MESSAGES = "))
        payload = json.loads(script[len("window.NPT_MESSAGES = "):].rstrip().rstrip(";"))
        self.assertEqual(len(payload), len(messages.MESSAGES))


class ApiLanguageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-i18n-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "config.json"
        patcher = patch.dict(os.environ, NET_PROXY_CONFIG=str(self.path))
        patcher.start()
        self.addCleanup(patcher.stop)
        instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ProxyConsoleHandler)
        worker = threading.Thread(target=instance.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(instance.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(instance.shutdown)
        self.web = instance

    def request(self, path, language=None, method="GET", body=None):
        connection = http.client.HTTPConnection(*self.web.server_address, timeout=6)
        try:
            headers = {"Host": "127.0.0.1:{}".format(self.web.server_port)}
            if language:
                headers["X-NPT-Language"] = language
            payload = None
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                headers["Content-Type"] = "application/json"
            connection.request(method, path, payload, headers)
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_the_catalogue_is_served_as_a_script(self):
        status, content_type, body = self.request("/api/i18n.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", content_type)
        self.assertTrue(body.startswith(b"window.NPT_MESSAGES = "))

    def test_an_api_error_follows_the_request_language(self):
        status, _, body = self.request("/api/gateways/delete", method="POST", body={})
        self.assertEqual(status, 400)
        self.assertIn("网关ID不能为空".encode("utf-8"), body)
        english_status, _, english = self.request("/api/gateways/delete", language="en",
                                                 method="POST", body={})
        self.assertEqual(english_status, 400)
        self.assertIn(b"The gateway id cannot be empty", english)

    def test_an_unknown_language_keeps_the_default(self):
        status, _, body = self.request("/api/gateways/delete", language="fr",
                                       method="POST", body={})
        self.assertEqual(status, 400)
        self.assertIn("网关ID不能为空".encode("utf-8"), body)


if __name__ == "__main__":
    unittest.main()
