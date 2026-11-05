"""Offline regressions: no real credentials and no real network requests."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from zlibrary.eapi import EAPIClient


class CookieIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_cookie_isolation_and_redirect(self):
        owner = EAPIClient("library.test", "123", "FAKE-SESSION")
        seen = []

        async def handle(request):
            seen.append((request.url.host, request.headers.get("cookie", "")))
            if request.url.path.endswith("/file"):
                return httpx.Response(
                    200, json={"downloadLink": "https://library.test/start"}
                )
            if request.url.path == "/start":
                return httpx.Response(
                    302, headers={"location": "https://cdn.test/book.pdf"}
                )
            return httpx.Response(200, content=b"%PDF-1.4\nOFFLINE TEST")

        real_client = httpx.AsyncClient

        def factory(**kwargs):
            return real_client(transport=httpx.MockTransport(handle), **kwargs)

        try:
            with tempfile.TemporaryDirectory() as directory:
                with patch("zlibrary.eapi.httpx.AsyncClient", side_effect=factory):
                    output = await owner.download_file(1, "hash", directory)
                    self.assertTrue(Path(output).is_file())
            self.assertTrue(
                any(
                    "FAKE-SESSION" in cookie
                    for host, cookie in seen
                    if host == "library.test"
                )
            )
            self.assertEqual(
                [cookie for host, cookie in seen if host == "cdn.test"], [""]
            )
        finally:
            await owner.close()

    async def test_external_initial_download_has_no_cookie(self):
        owner = EAPIClient("library.test", "123", "FAKE-SESSION")
        client = httpx.AsyncClient(cookies=owner._scoped_cookies())
        try:
            request = client.build_request("GET", "https://cdn.test/book.pdf")
            await owner._guard_request(request)
            self.assertNotIn("cookie", request.headers)
            for url in [
                "https://sub.library.test/file",
                "https://library.test:8443/file",
            ]:
                request = client.build_request("GET", url, headers={"cookie": "leaked"})
                await owner._guard_request(request)
                self.assertNotIn("cookie", request.headers)
        finally:
            await client.aclose()

    async def test_http_is_refused(self):
        owner = EAPIClient("library.test", "123", "FAKE-SESSION")
        with self.assertRaises(RuntimeError):
            await owner._guard_request(httpx.Request("GET", "http://library.test/file"))

    async def test_login_redirect_is_not_followed(self):
        owner = EAPIClient("library.test")
        seen = []

        def handle(request):
            seen.append(request.url.host)
            return httpx.Response(
                307, headers={"location": "https://external.test/login"}
            )

        real_client = httpx.AsyncClient

        def factory(**kwargs):
            return real_client(transport=httpx.MockTransport(handle), **kwargs)

        try:
            with patch("zlibrary.eapi.httpx.AsyncClient", side_effect=factory):
                with self.assertRaises(RuntimeError):
                    await owner.login("fake@example.test", "FAKE-PASSWORD")
            self.assertEqual(seen, ["library.test"])
        finally:
            await owner.close()


class LoggerPolicyTests(unittest.TestCase):
    def test_no_automatic_file_logging(self):
        # pytest attaches its own file/capture handlers; inspect a fresh process.
        source = Path(__file__).resolve().parents[2] / "zlibrary" / "src"
        code = """import json, logging
from zlibrary.logger import logger
print(json.dumps({
    "handlers": len(logger.handlers),
    "file_handlers": any(isinstance(h, logging.FileHandler) for h in logger.handlers),
    "error_only": all(h.level >= logging.ERROR for h in logger.handlers),
}))
"""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": os.defpath,
                    "PYTHONPATH": str(source),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            state = json.loads(result.stdout)
            self.assertGreater(state["handlers"], 0)
            self.assertFalse(state["file_handlers"])
            self.assertTrue(state["error_only"])
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
