"""Compatibility of the built-in diagnostic target list and private overrides."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sdk.config import DEFAULT_TEST_URL, load_config

OLD_URLS = {"Google": "https://www.google.com", "GitHub": "https://github.com",
            "Raw GitHub": "https://raw.githubusercontent.com", "HuggingFace": "https://huggingface.co",
            "PyPI": "https://pypi.org", "OpenAI API": "https://api.openai.com", "YouTube": "https://www.youtube.com"}
REQUIRED = {"Google", "Claude", "ChatGPT", "YouTube", "Gemini"}


class SiteDefaults(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "config.json"
        env = patch.dict(os.environ, NET_PROXY_CONFIG=str(self.path))
        env.start()
        self.addCleanup(env.stop)

    def test_clean_defaults_and_original_factory_settings(self):
        defaults = load_config()["diagnostic_targets"]
        self.assertEqual(defaults["Google"]["url"], DEFAULT_TEST_URL)
        self.assertTrue(REQUIRED <= defaults.keys())
        self.assertFalse(self.path.exists())
        template = json.loads((Path(__file__).resolve().parents[1] / "config.example.json").read_text(encoding="utf-8"))
        self.assertEqual({k: v["url"] for k, v in defaults.items()},
                         {k: v["url"] for k, v in template["diagnostic_targets"].items()})
        old_generated = {n: {"url": u, "desc": n, "category": "HTTPS"} for n, u in OLD_URLS.items()}
        old_example = {n: dict(template["diagnostic_targets"][n], url=u) for n, u in OLD_URLS.items()}
        for original in (old_generated, old_example):
            before = json.dumps({"diagnostic_targets": original}).encode()
            self.path.write_bytes(before)
            actual = load_config()["diagnostic_targets"]
            self.assertTrue(REQUIRED <= actual.keys())
            self.assertEqual(actual["GitHub"], original["GitHub"])
            self.assertEqual(actual["Google"]["url"], DEFAULT_TEST_URL)
            self.assertEqual(self.path.read_bytes(), before)

    def test_custom_lists_including_empty_strings_and_edited_metadata(self):
        edited = {n: {"url": u, "desc": n, "category": "HTTPS"} for n, u in OLD_URLS.items()}
        edited["Google"]["desc"] = "My workload"
        for custom in ({}, {"My probe": "https://test.invalid/health"}, edited):
            self.path.write_text(json.dumps({"diagnostic_targets": custom}), encoding="utf-8")
            self.assertEqual(load_config()["diagnostic_targets"], custom)
