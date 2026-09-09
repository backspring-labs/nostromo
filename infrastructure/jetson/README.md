# Jetson: Buzz relay appliance

Runbook for WP-2 of NOSTROMO-PLAN-0001. The Jetson Orin Nano Super (`nano`, Tailscale `nano.tailc69e7d.ts.net`, `100.98.252.95`) runs the pinned Buzz production Compose stack and nothing else of Nostromo's. Everything here is driven from the owner's Mac over Tailscale SSH. The Nostromo repo is never cloned on the Jetson and no GitHub credential is placed there (Jetson handoff pack, plan §20).

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

The relay publishes on `100.98.252.95:3000` (tailnet) and `127.0.0.1:3000` and `127.0.0.1:8080` (loopback). It never binds `0.0.0.0`, so the LAN address refuses connections and nothing is reachable from the public Internet. Tailscale Funnel must never be enabled.

## TLS (pending two owner actions)

The relay currently answers `ws://nano.tailc69e7d.ts.net:3000` in the clear over the tailnet, which the plan allows for bootstrap (§9.6). Moving to `wss://` needs:

1. In the Tailscale admin console, DNS page, enable **HTTPS Certificates** for the tailnet. Until then `tailscale status --json` reports `CertDomains: null` on the nano.
2. On the nano, once: `sudo tailscale set --operator=jladd` so Serve can be configured without root.

Then, from the Mac:

```bash
ssh nano 'tailscale serve --bg --https=443 http://127.0.0.1:3000 && tailscale serve status'
```

and change these five lines in `buzz/buzz.env`, then run `install.sh`:

```text
RELAY_URL=wss://nano.tailc69e7d.ts.net
BUZZ_MEDIA_BASE_URL=https://nano.tailc69e7d.ts.net/media
BUZZ_MEDIA_SERVER_DOMAIN=nano.tailc69e7d.ts.net
BUZZ_CORS_ORIGINS=https://nano.tailc69e7d.ts.net
```

Never `tailscale funnel`. The same steps apply, with the new name, at the hostname switch below.

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

The Tailscale name is the bootstrap value. Before WP-5 mints identities the relay moves to `buzz.backspring.xyz` (plan §9.6, `crew/manifest.yaml`). That is a certificate (DNS-01) plus the same five `buzz.env` lines and `relay.hostname` in the manifest, in one commit.

## Known constraints on the Jetson

- `sudo` prompts for a password, so anything needing root (Tailscale Serve setup, reboot) is an owner action typed at the prompt with the `!` prefix.
- The reboot-persistence probe is therefore still open. Docker's restart policy will bring the stack back; confirm with `probe.sh` after the first reboot.
- A native Ollama listens on loopback port 11434 on the nano. It is unrelated to Buzz and was left alone.
