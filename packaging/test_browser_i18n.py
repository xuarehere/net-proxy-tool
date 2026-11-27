"""Check the console in both languages in Chromium."""
import argparse
from contextlib import ExitStack, contextmanager
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web import server  # noqa: E402


@contextmanager
def listener(handler):
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield httpd
        finally:
            httpd.shutdown()
            thread.join()


def run():
    with ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(patch.dict(os.environ, {"NET_PROXY_CONFIG": str(temp / "config.json")}))
        console = stack.enter_context(listener(server.ProxyConsoleHandler))
        url = "http://127.0.0.1:" + str(console.server_port)

        p = stack.enter_context(sync_playwright())
        browser = p.chromium.launch(executable_path=p.chromium.executable_path)
        stack.callback(browser.close)

        # A browser that asks for Chinese gets Chinese.
        chinese = browser.new_page()
        chinese.add_init_script("try { localStorage.setItem('npt-lang', 'zh-CN'); } catch (error) {}")
        chinese.goto(url)
        expect(chinese.locator("#setup-title")).to_have_text("连接你的 HTTP 代理")
        expect(chinese.locator("#setup-test")).to_have_text("发送代理请求")
        expect(chinese.locator("#lang-toggle")).to_have_text("EN")
        chinese.close()

        # A browser that asks for English gets English.
        english = browser.new_page()
        english.add_init_script(
            "try { if (!sessionStorage.getItem('npt-i18n-init')) {"
            " sessionStorage.setItem('npt-i18n-init', '1');"
            " localStorage.setItem('npt-lang', 'en'); } } catch (error) {}"
        )
        english.goto(url)
        expect(english.locator("#setup-title")).to_have_text("Connect your HTTP proxy")
        expect(english.locator("#setup-test")).to_have_text("Send a proxy request")
        expect(english.locator("#lang-toggle")).to_have_text("中文")
        expect(english.locator("html")).to_have_attribute("lang", "en")

        # The toggle switches the language and remembers it.
        english.locator("#lang-toggle").click()
        expect(english.locator("#setup-title")).to_have_text("连接你的 HTTP 代理")
        expect(english.locator("#lang-toggle")).to_have_text("EN")
        english.reload()
        expect(english.locator("#setup-title")).to_have_text("连接你的 HTTP 代理")
        english.close()

        # A browser without a preference follows its own language list.
        default = browser.new_page()
        default.add_init_script("try { localStorage.removeItem('npt-lang'); } catch (error) {}")
        default.goto(url)
        chosen = default.evaluate("window.nptI18n.language()")
        assert chosen in ("en", "zh-CN"), chosen
        default.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run()
    print("Console language checks passed.")
