"""Keep crew model harnesses out of squad execution. Never stop or unload TensorFold."""
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .core import Refused


class Window:
    def __init__(self, flag, run=subprocess.run, meminfo="/proc/meminfo"):
        self.flag, self.run, self.meminfo = Path(flag), run, Path(meminfo)

    def unit(self, verb, role):
        result = self.run(["systemctl", verb, "nostromo@" + role], capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout.strip()

    def close(self):
        # The ExecCondition sees this across reboot, before either crew launcher can run.
        memory = {}
        for line in self.meminfo.read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemAvailable", "SwapFree"}:
                memory[key] = value.strip()
        tmp = self.flag.with_suffix(".tmp")
        tmp.write_text(json.dumps({"closed_at": time.time(), "memory": memory}) + "\n")
        tmp.chmod(0o644)
        tmp.replace(self.flag)
        self.flag.with_name("crew-window-lease").unlink(missing_ok=True)
        for role in ("mother", "brett"):
            code, _ = self.unit("stop", role)
            if code:
                raise Refused("could not stop local role " + role + "; squad action was not submitted")
            result = self.run(["systemctl", "show", "nostromo@" + role, "-p", "ActiveState", "-p", "MainPID"],
                              capture_output=True, text=True, timeout=10)
            props = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            if result.returncode or props.get("ActiveState") != "inactive" or props.get("MainPID") != "0":
                raise Refused("local role did not become quiescent: " + role)

    def open(self, expires_at):
        deadline = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp()
        if deadline - time.time() < 90:
            raise Refused("lease is too close to expiry to admit a local inference window")
        lease_file = self.flag.with_name("crew-window-lease")
        lease_file.write_text(str(deadline) + "\n")
        lease_file.chmod(0o644)
        self.flag.unlink(missing_ok=True)
        for role in ("mother", "brett"):
            enabled, state = self.unit("is-enabled", role)
            if enabled == 0 and state == "enabled":
                code, _ = self.unit("start", role)
                if code:
                    self.close()
                    raise Refused("local role failed to start inside the held lease")

    def expire(self):
        path = self.flag.with_name("crew-window-lease")
        try:
            deadline = float(path.read_text())
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            self.close()
            return
        if time.time() >= deadline - 60:
            self.close()


def startup_check():
    flag = Path("/var/lib/nostromo-campaign-broker/squad-window")
    try:
        flag.stat()
    except FileNotFoundError:
        try:
            deadline = float(flag.with_name("crew-window-lease").read_text())
        except FileNotFoundError:
            return 0
        except (OSError, ValueError):
            return 1
        return 0 if deadline - time.time() >= 60 else 1
    except OSError:
        return 1
    return 1
