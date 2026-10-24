#!/usr/bin/env python3
"""Owner-side preparation: create three scoped JWT-authenticated clients; never print credentials.

Runs as the owner on the Spark. The existing Keycloak bootstrap admin credential is read in
memory from its container. New signing keys remain in a 0700 staging directory until the root
installer moves them to the broker. No client is given admin or campaigns:control.
"""
import argparse
import json
import os
import pwd
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from runtime.campaigns.auth import API

CLIENTS = {"control": ("campaign-operations", ["campaign-supervisor"]),
           "review": ("campaign-review", ["campaign-supervisor", "operator"]),
           "read": ("campaign-evidence", ["campaign-triage"])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--realm", default="squadops-local")
    p.add_argument("--keycloak", default="http://spark:8180")
    p.add_argument("--keycloak-connect", default="http://127.0.0.1:8180", help="host-local transport; issuer stays --keycloak")
    p.add_argument("--api", default="http://127.0.0.1:8001")
    p.add_argument("--staging", default=str(Path.home()/".config/nostromo/campaign-provision"))
    p.add_argument("--channels", nargs="+", required=True, help="decision channel UUIDs, not names")
    args = p.parse_args()
    os.umask(0o077)
    staging = Path(args.staging)
    staging.mkdir(parents=True, exist_ok=True, mode=0o700)
    if staging.is_symlink() or staging.stat().st_mode & 0o077:
        raise SystemExit("staging directory must be owner-only and not a symlink")
    info = json.loads(subprocess.run(["docker", "inspect", "squadops-keycloak"],
                                    capture_output=True, text=True, check=True).stdout)[0]
    env = dict(x.split("=", 1) for x in info["Config"]["Env"] if "=" in x)
    username = env.get("KC_BOOTSTRAP_ADMIN_USERNAME") or env.get("KEYCLOAK_ADMIN")
    password = env.get("KC_BOOTSTRAP_ADMIN_PASSWORD") or env.get("KEYCLOAK_ADMIN_PASSWORD")
    form = urllib.parse.urlencode({"grant_type": "password", "client_id": "admin-cli",
                                   "username": username, "password": password}).encode()
    headers = {"Host": urllib.parse.urlsplit(args.keycloak).netloc}
    req = urllib.request.Request(args.keycloak_connect + "/realms/master/protocol/openid-connect/token", data=form, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        admin = json.load(response)["access_token"]

    def kc(method, suffix, body=None):
        raw = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(args.keycloak_connect + "/admin/realms/" + args.realm + suffix,
            data=raw, method=method, headers={**headers, "Authorization": "Bearer " + admin, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read()
        return json.loads(data) if data else None

    config = {"api_url": args.api, "clients": {}, "public_keys": {}, "callers": {},
              "decision_channels": args.channels, "decision_ttl_s": 1800,
              "database": "/var/lib/nostromo-campaign-broker/control.sqlite3",
              "window_flag": "/var/lib/nostromo-campaign-broker/squad-window",
              "socket": "/run/nostromo-campaigns/control.sock"}
    import yaml
    manifest = yaml.safe_load((ROOT/"crew/manifest.yaml").read_text())
    config["watcher_auth_tag"] = manifest["agents"]["mother"]["buzz_auth_tag"]
    if manifest["agents"]["mother"]["model"] != manifest["agents"]["brett"]["model"]:
        raise SystemExit("shared inference requires matching pinned Mother/Brett models")
    config["shared_model"] = manifest["agents"]["mother"]["model"]
    for role, entry in manifest["agents"].items():
        config["public_keys"][role] = entry["buzz_pubkey"]
        config["callers"][str(pwd.getpwnam(role).pw_uid)] = role
    config["public_keys"]["owner"] = manifest["owner"]["buzz_pubkey"]
    config["callers"][str(os.getuid())] = "owner"
    created = []
    try:
        for principal, (client_id, roles) in CLIENTS.items():
            key = staging/(principal + ".pem")
            if not key.exists():
                subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)],
                               capture_output=True, check=True)
            key.chmod(0o600)
            public = subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"],
                                    capture_output=True, text=True, check=True).stdout
            encoded = "".join(line for line in public.splitlines() if not line.startswith("---"))
            kid = "campaign-" + principal + "-v1"
            held = kc("GET", "/clients?clientId=" + client_id)
            if held:
                client = held[0]
                if client.get("attributes", {}).get("nostromo.managed_by") != "campaign-broker-v1":
                    raise RuntimeError("existing client is not owned by this installer: " + client_id)
                # Refuse key replacement: rerunning preparation must not silently rotate credentials.
                if client.get("attributes", {}).get("jwt.credential.public.key") != encoded:
                    raise RuntimeError("registered client key differs from staging: " + client_id)
            else:
                client = {"clientId": client_id, "name": client_id, "enabled": True, "protocol": "openid-connect",
                    "publicClient": False, "clientAuthenticatorType": "client-jwt", "serviceAccountsEnabled": True,
                    "standardFlowEnabled": False, "directAccessGrantsEnabled": False, "fullScopeAllowed": False,
                    "attributes": {"nostromo.managed_by": "campaign-broker-v1", "use.jwks.url": "false",
                                   "jwt.credential.public.key": encoded, "jwt.credential.kid": kid,
                                   "token.endpoint.auth.signing.alg": "RS256"},
                    "defaultClientScopes": ["roles"],
                    "protocolMappers": [{"name": "runtime-api-audience", "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper", "consentRequired": False,
                        "config": {"included.client.audience": "squadops-runtime", "id.token.claim": "false", "access.token.claim": "true"}}]}
                kc("POST", "/clients", client)
                client = kc("GET", "/clients?clientId=" + client_id)[0]
                created.append(client["id"])
            account = kc("GET", "/clients/" + client["id"] + "/service-account-user")
            resolved = [kc("GET", "/roles/" + role) for role in roles]
            kc("POST", "/users/" + account["id"] + "/role-mappings/realm", resolved)
            kc("POST", "/clients/" + client["id"] + "/scope-mappings/realm", resolved)
            actual = kc("GET", "/users/" + account["id"] + "/role-mappings/realm/composite")
            names = {role["name"] for role in actual}
            if "admin" in names or not set(roles) <= names:
                raise RuntimeError("service role mapping failed")
            config["clients"][principal] = {"client_id": client_id, "key_file": str(key), "kid": kid,
                "token_url": args.keycloak + "/realms/" + args.realm + "/protocol/openid-connect/token",
                "token_connect_url": args.keycloak_connect + "/realms/" + args.realm + "/protocol/openid-connect/token"}
            if principal == "control":
                config["control_principal"] = account["id"]
            print(principal + ": separate signed-JWT client, roles " + ", ".join(roles), flush=True)
        api = API(config)
        for principal in CLIENTS:
            api(principal, "GET", "/api/v1/projects", None)
            print(principal + ": authenticated read through deployed API succeeded", flush=True)
        (staging/"config.json").write_text(json.dumps(config, indent=2) + "\n")
        print("Prepared configuration and owner-only keys at " + str(staging))
    except Exception as e:
        # A partial first provisioning is not left with enabled, unverified client grants.
        for cid in created:
            try:
                kc("DELETE", "/clients/" + cid)
            except Exception:
                pass
        print("Provisioning failed; newly created clients removed. " + type(e).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
