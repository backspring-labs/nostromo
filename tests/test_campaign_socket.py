"""Linux integration proof: caller identity comes from SO_PEERCRED, never request JSON."""
import json
import os
import socket
import sys
import threading
import subprocess
import time
from unittest import TestCase, skipUnless

from runtime.campaigns.cli import call
from runtime.campaigns.core import Refused
from runtime.campaigns.service import Server


@skipUnless(sys.platform == "linux", "SO_PEERCRED is the production Linux boundary")
class SocketBoundary(TestCase):
    def test_production_daemon_shares_only_socket_not_approval_database(self):
        import tempfile
        from pathlib import Path
        import runtime.campaigns.service as service
        with tempfile.TemporaryDirectory(prefix="campaign-daemon-") as directory:
            root = Path(directory)
            config = {"callers": {str(os.getuid()): "owner"}, "clients": {},
                      "database": str(root/"state.sqlite3"), "window_flag": str(root/"flag"),
                      "socket": str(root/"control.sock")}
            (root/"config.json").write_text(json.dumps(config))
            process = subprocess.Popen([sys.executable, "-m", "runtime.campaigns.service", "--config", str(root/"config.json")],
                                       cwd=Path(service.__file__).resolve().parents[2],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not (root/"control.sock").exists() and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(0.02)
                self.assertIsNone(process.poll(), "production daemon failed to start")
                self.assertEqual(call({"command": "tracked", "args": {}}, config["socket"]), [])
                self.assertEqual((root/"control.sock").stat().st_mode & 0o777, 0o660)
                self.assertEqual((root/"state.sqlite3").stat().st_mode & 0o777, 0o600)
            finally:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()

    def test_kernel_uid_admission_and_spoof_refusals(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="campaign-peer-") as directory:
            root = Path(directory)
            config = {"callers": {str(os.getuid()): "mother"}, "clients": {},
                      "database": str(root/"state.sqlite3"), "window_flag": str(root/"flag")}
            server = Server(str(root/"control.sock"), config)
            calls = []
            def forbidden_api(*args):
                calls.append(args)
                raise AssertionError("refused request reached API")
            server.api = forbidden_api
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(call({"command": "tracked", "args": {}}, str(root/"control.sock")), [])
                for request, error in [
                    ({"command": "increment", "args": {}, "request_id": "probe"}, "belong to Ripley"),
                    ({"command": "tracked", "args": {}, "caller": "owner"}, "unexpected"),
                    ({"command": "create", "args": {"definition": "absent", "reason": "probe"},
                      "request_id": "unapproved"}, "not owner-approved"),
                ]:
                    with self.assertRaisesRegex(Refused, error):
                        call(request, str(root/"control.sock"))
                config["callers"] = {}
                with self.assertRaisesRegex(Refused, "Unix caller is not admitted"):
                    call({"command": "tracked", "args": {}}, str(root/"control.sock"))
                self.assertEqual(calls, [])
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
