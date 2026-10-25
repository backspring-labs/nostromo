"""Short-lived private_key_jwt authentication. No token files or credentials in argv."""
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .core import Refused, canonical


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def assertion(client, now=None):
    now = int(time.time()) if now is None else now
    header = b64(canonical({"alg": "RS256", "typ": "JWT", "kid": client["kid"]}).encode())
    claims = {"iss": client["client_id"], "sub": client["client_id"], "aud": client["token_url"],
              "iat": now, "exp": now + 60, "jti": str(uuid.uuid4())}
    message = (header + "." + b64(canonical(claims).encode())).encode()
    key = Path(client["key_file"])
    if key.is_symlink() or key.stat().st_mode & 0o077:
        raise Refused("client signing key must be an owner-only regular file")
    result = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key)],
                            input=message, capture_output=True, timeout=10)
    if result.returncode:
        raise Refused("client assertion signing failed")
    return message.decode() + "." + b64(result.stdout)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    def __init__(self, config):
        self.config = config
        self.opener = urllib.request.build_opener(NoRedirect)
        self.tokens = {}

    def host(self):
        """Fixed, read-only public health route; never a caller-supplied URL or API pass-through."""
        request = urllib.request.Request(self.config["api_url"].rstrip("/") + "/health/host")
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError()
            return json.loads(raw)
        except (OSError, ValueError):
            raise Refused("runtime box state unreadable; shared inference stays closed") from None

    def token(self, principal):
        held = self.tokens.get(principal)
        if held and held[1] > time.time() + 20:
            return held[0]
        c = self.config["clients"][principal]
        form = {"grant_type": "client_credentials", "client_id": c["client_id"],
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": assertion(c)}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        connect_url = c.get("token_connect_url", c["token_url"])
        if connect_url != c["token_url"]:
            # Host-local routing preserves the API's configured issuer without relaxing TLS policy.
            headers["Host"] = urllib.parse.urlsplit(c["token_url"]).netloc
        request = urllib.request.Request(connect_url, data=urllib.parse.urlencode(form).encode(), headers=headers)
        try:
            with self.opener.open(request, timeout=15) as response:
                data = json.loads(response.read(65536))
            token = data["access_token"]
            self.tokens[principal] = token, time.time() + min(int(data["expires_in"]), 300)
            return token
        except Exception:
            raise Refused("service authentication failed; ask the owner to check provisioning") from None

    def __call__(self, principal, method, path, body):
        raw = self.request(principal, method, path, body)
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            raise Refused("SquadOps response is not JSON") from None

    def request(self, principal, method, path, body, *, limit=1048576, page=None):
        if not path.startswith("/api/v1/") or ".." in path or "?" in path:
            raise Refused("invalid internal API path")
        if page is not None:
            # Only internal evidence readers construct paging, never caller-supplied queries.
            offset, count = page
            if type(offset) is not int or not 0 <= offset <= 2000 or count != 100:
                raise Refused("invalid evidence page")
            path += "?" + urllib.parse.urlencode({"offset": offset, "limit": count})
        token = self.token(principal)
        request = urllib.request.Request(self.config["api_url"].rstrip("/") + path,
                                         data=None if body is None else canonical(body).encode(),
                                         method=method, headers={"Authorization": "Bearer " + token,
                                                                 "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(limit + 1)
            if len(raw) > limit:
                raise Refused("API response exceeds the evidence packet limit")
            return raw
        except urllib.error.HTTPError as e:
            # Error bodies may echo inputs or sensitive internal context. Return status, never tokens.
            raise Refused(f"SquadOps refused the operation (HTTP {e.code}); inspect its control log") from None
        except (OSError, ValueError):
            raise Refused("SquadOps response unreadable; do not infer success or retry a write") from None
