"""Unix-socket broker; the kernel identifies callers, not request parameters."""
import argparse
import json
import os
import pwd
import socket
import socketserver
import struct
from pathlib import Path

from .auth import API
from .core import Broker, Refused, Store, canonical
from .decisions import verifier
from .host import Window

MAX_REQUEST = 524288


class Server(socketserver.UnixStreamServer):
    def __init__(self, path, config):
        self.config = config
        self.api = API(config)
        super().__init__(path, Handler)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(60)
        store = None
        try:
            _pid, uid, _gid = struct.unpack("3i", self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            caller = self.server.config["callers"].get(str(uid))
            if caller is None:
                raise Refused("Unix caller is not admitted")
            line = self.rfile.readline(MAX_REQUEST + 1)
            if len(line) > MAX_REQUEST or not line.endswith(b"\n"):
                raise Refused("request is incomplete or too large")
            request = json.loads(line)
            store = Store(self.server.config["database"])
            broker = Broker(store, self.server.api, self.server.config, verifier(self.server.config),
                            Window(self.server.config["window_flag"]))
            result = {"ok": True, "result": broker.handle(caller, request)}
        except Refused as e:
            result = {"ok": False, "error": str(e)}
        except Exception:
            # Neither server exceptions nor request bodies enter logs or response traces.
            result = {"ok": False, "error": "broker operation failed; owner inspection required"}
        finally:
            if store:
                store.db.close()
        self.wfile.write(canonical(result).encode() + b"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="/etc/nostromo/campaign-broker.json")
    args = p.parse_args()
    config = json.loads(Path(args.config).read_text())
    os.umask(0o007)
    path = Path(config["socket"])
    if path.exists():
        path.unlink()
    server = Server(str(path), config)
    path.chmod(0o660)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
