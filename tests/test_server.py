import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from peogai.demo import DemoController, reset_demo
from peogai.server import make_server
from peogai.model import SYSTEM_PROMPT
from peogai.workspace import snapshot

PROJECT = Path(__file__).resolve().parents[1]
TEMP = PROJECT / ".peogai" / "test-tmp"
TEMP.mkdir(parents=True, exist_ok=True)


class ServerTests(unittest.TestCase):
    def test_dashboard_and_reset_request_boundary(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP) as temp:
            root = Path(temp)
            snapshot(PROJECT / "fixtures/demo", root / "fixtures/demo")
            reset_demo(root)
            controller = DemoController("fake", 1, root)
            server = make_server(controller, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            url = f"http://127.0.0.1:{server.server_port}"
            try:
                with opener.open(url) as response:
                    self.assertIn(b"Patch inspector", response.read())
                with opener.open(url + "/api/state") as response:
                    state = json.load(response)
                self.assertEqual(state["system_prompt"], SYSTEM_PROMPT)
                self.assertEqual(len(state["issues"]), 6)
                request = urllib.request.Request(url + "/api/reset", method="POST")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(request)
                self.assertEqual(error.exception.code, 403)
                stale = urllib.request.Request(url + "/api/approve", method="POST", headers={
                    "X-Demo-Token": state["token"]}, data=b'{"review_id":"stale"}')
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(stale)
                self.assertEqual(error.exception.code, 409)
                bad_origin = urllib.request.Request(url + "/api/reset", method="POST", headers={
                    "X-Demo-Token": state["token"], "Origin": "https://example.com"})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(bad_origin)
                self.assertEqual(error.exception.code, 403)
                marker = root / "demo" / "extra.txt"
                marker.write_text("temporary")
                request.add_header("X-Demo-Token", state["token"])
                with opener.open(request) as response:
                    self.assertEqual(response.status, 200)
                self.assertFalse(marker.exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
