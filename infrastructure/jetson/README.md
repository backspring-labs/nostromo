# Jetson: Buzz relay appliance

Runbook for WP-2 of Bootstrap Plan. The Jetson Orin Nano Super (`nano`, Tailscale `nano.tailc69e7d.ts.net`, `100.98.252.95`) runs the pinned Buzz production Compose stack and nothing else of Nostromo's. Everything here is driven from the owner's Mac over Tailscale SSH. The Nostromo repo is never cloned on the Jetson and no GitHub credential is placed there (Jetson handoff pack, plan §20).

## What is where

Repo (`infrastructure/jetson/`):

| Path | Purpose |
|---|---|
| `buzz/upstream.lock` | Pinned block/buzz commit, image digests, sha256 of the upstream Compose file |
| `buzz/compose.nostromo.yml` | The only overlay: port binding, env-file split, every dependency image pinned by digest |
| `buzz/buzz.env` | Non-secret relay configuration, synced verbatim to the Jetson on every install |
| `buzz/secrets.env.template` | Shape of the host-generated secrets file; never instantiated in the repo |
| `bin/install.sh` | Mac side: fetch upstream Compose at the pin, verify hash, sync, bootstrap |
| `bin/bootstrap-remote.sh` | Jetson side: generate secrets once, pull, start |
| `bin/buzzctl` | Jetson side: wrapper for the Compose stack and `buzz-admin` |
| `bin/backup.sh` | Jetson side: recovery copy of secrets, Postgres, and volumes |
| `bin/probe.sh` | Mac side: health and boundary probes, prints evidence |
| `evidence/` | Captured WP-2 evidence (plan §9.10), no secrets |

Jetson (`/mnt/ssd/buzz/`, NVMe, mode 700):

| Path | Purpose |
|---|---|
| `deploy/compose.yml` | Upstream file fetched at the pinned commit |
| `deploy/compose.nostromo.yml`, `deploy/buzz.env`, `deploy/buzzctl`, `deploy/backup.sh` | Synced from the repo |
| `deploy/secrets.env` | Host-generated, mode 600, never leaves the host except inside a backup set |
| `deploy/relay.pubkey` | The relay's signing public key (also visible as `self` in NIP-11) |
| `deploy/owner.placeholder.pubkey` | The placeholder owner pubkey, see "Owner identity" |
| `backups/<UTC stamp>/` | Backup sets, newest seven kept |

Durable state lives in named Docker volumes under the Docker data root, which is on the NVMe: `/mnt/ssd/docker/volumes/buzz-prod_buzz-{postgres,redis,minio,git}-data`. The root filesystem is the microSD and holds no Buzz state.

## Install or update

```bash
infrastructure/jetson/bin/install.sh        # from the repo root on the Mac
infrastructure/jetson/bin/probe.sh          # then prove it
```

`install.sh` is idempotent. It refuses to run if the upstream Compose file no longer matches the hash in `upstream.lock` or if `buzz.env` names a different image than the lock. Re-running syncs the repo-managed files and restarts the stack; `secrets.env` is never rewritten.

To upgrade Buzz: resolve the new image index digest and its source commit, update `upstream.lock`, `buzz.env`, and `docs/source-baseline.md` together, run `backup.sh`, then `install.sh`.

On the Jetson, `buzzctl` gives `start`, `stop`, `restart`, `status`, `logs`, `config`, `admin <buzz-admin args>`, and `backup`.

## Network boundary

The relay publishes on loopback only: `127.0.0.1:3000` (app, WebSocket, REST) and `127.0.0.1:8080` (liveness and readiness). Tailscale Serve listens on 443 on the tailnet address and proxies to 3000, so the only way in is `wss://nano.tailc69e7d.ts.net` from a tailnet device. The plaintext port is closed to the tailnet, the LAN address refuses on both 3000 and 443, and nothing is reachable from the public Internet. Tailscale Funnel must never be enabled.

Connect by hostname, never by IP. The relay is multi-tenant: at startup it ensures a community row for the host in `RELAY_URL`, and every WebSocket is bound to a community by the request `Host` header. Any other host, including `100.98.252.95`, gets a generic 404 (`relay: no community is configured for this host`). NIP-11 at `/` is served regardless, so a passing NIP-11 probe does not prove the WebSocket path; `probe.sh` checks the `101` upgrade separately.

## TLS

Tailscale Serve terminates TLS with a Let's Encrypt certificate for `nano.tailc69e7d.ts.net`. Prerequisites done on 2026-09-08 by the owner: HTTPS Certificates enabled for the tailnet in the admin console, and `sudo tailscale set --operator=jladd` on the nano. The Serve configuration was then applied from the Mac:

```bash
ssh nano 'tailscale serve --bg --https=443 http://127.0.0.1:3000'
```

It persists in tailscaled state across reboots; `ssh nano tailscale serve status` must always show `(tailnet only)`. Tailscale renews the certificate itself. To take Serve down: `tailscale serve --https=443 off`. Never `tailscale funnel`.

Serve only serves the MagicDNS name, so it does not carry over to the hostname switch below. `buzz.backspring.xyz` needs its own terminator with a DNS-01 certificate: the upstream-supported path is `compose.caddy.yml` with a Caddy build that has the DNS provider plugin, proxying to the relay on loopback exactly as Serve does now.

## Owner identity

Closed mode (`BUZZ_REQUIRE_RELAY_MEMBERSHIP=true`) refuses to start without `RELAY_OWNER_PUBKEY`. The owner keypair is on hold until WP-3, so `buzz.env` carries a **placeholder** owner pubkey generated on the Jetson with `buzz-admin generate-key`; its secret was piped to `awk` and never written anywhere. Nobody can act as that owner, the relay is closed and inert, and the well-known NIP-05 map is empty.

At WP-3, once the real owner pubkey exists:

1. Put it in `buzz.env` as `RELAY_OWNER_PUBKEY` and run `install.sh`. On start the relay upserts the new owner and demotes the placeholder to `admin`.
2. Remove the placeholder from the roster: `ssh nano '/mnt/ssd/buzz/deploy/buzzctl admin remove-member --pubkey $(cat /mnt/ssd/buzz/deploy/owner.placeholder.pubkey) --role admin'`, then delete `owner.placeholder.pubkey`.
3. Verify with `buzzctl admin list-members`.

If nothing has been stored yet, the cleaner alternative is to stop the stack, remove the four `buzz-prod_buzz-*-data` volumes, and start again. The relay identity is in `secrets.env` and survives that.

## Secrets

`secrets.env` holds the relay signing key, git hook HMAC secret, Postgres and Redis passwords, and MinIO credentials. Generated once on first bootstrap, mode 600, owner `jladd`. Rotating any of them is a deliberate operation: back up first, edit, `buzzctl restart` (relay) or recreate the affected service. Rotating the relay signing key changes the relay's identity and breaks NIP-43 membership events, so treat it as a rebuild.

## Backup and restore

`ssh nano /mnt/ssd/buzz/deploy/backup.sh` writes `/mnt/ssd/buzz/backups/<stamp>/` with `secrets.env`, `buzz.env`, `upstream.lock`, `relay.pubkey`, a `pg_dump` custom-format dump, and tarballs of the git, minio, and redis volumes, plus `SHA256SUMS`. Copy the newest set off-host afterwards; the Mac copy lives at `~/.nostromo/backups/jetson/` (mode 700, outside any repo). Run it before every upgrade and before crew state accumulates (plan §9.9).

Restore on a fresh host: install, stop the stack, restore `secrets.env`, start Postgres alone and `pg_restore` the dump, untar the three volumes into their mountpoints, start the stack, check `probe.sh`.

## Hostname switch before WP-5

The Tailscale name is the bootstrap value. Before WP-5 mints identities the relay moves to `buzz.backspring.xyz` (plan §9.6, `crew/manifest.yaml`). Two facts shape the procedure:

- **A new host is a new community.** The `communities` table is keyed by host with create-if-missing semantics (`ensure_configured_community_for_bootstrap`, buzz-db). Changing `RELAY_URL` does not rename the existing community; it creates another one and bootstraps the owner there. There is no rename in `buzz-admin`. So the switch must happen while nothing worth keeping exists, and it should be done with a data reset so no stale community lingers: `buzzctl stop`, remove the four `buzz-prod_buzz-*-data` volumes, `buzzctl start`. The relay identity lives in `secrets.env` and survives the reset.
- **Serve does not carry over.** Tailscale Serve only serves the MagicDNS name, so `buzz.backspring.xyz` needs its own TLS terminator with a DNS-01 certificate. The upstream-supported path is `compose.caddy.yml` with a Caddy build that includes the DNS provider plugin, proxying to the relay on loopback exactly as Serve does now. Serve is then switched off.

The commit that performs the switch changes the four `buzz.env` URL lines and `BUZZ_DOMAIN`, `relay.hostname` in `crew/manifest.yaml`, and the handles in the manifest, together. The natural moment is WP-3, when the real owner pubkey replaces the placeholder, since that also wants a reset.

## Known constraints on the Jetson

- `sudo` prompts for a password, so anything needing root (a reboot, changing the Tailscale operator) is an owner action typed at the prompt with the `!` prefix. Serve itself no longer needs root because `jladd` is the Tailscale operator.
- Reboot recovery is proven (2026-09-08): tailscaled starts before Docker, the stack returns under its restart policy, Serve persists. Give the relay its start period, about 30 s after the container appears, before trusting `probe.sh`.
- A native Ollama listens on loopback port 11434 on the nano. It is unrelated to Buzz and was left alone.
