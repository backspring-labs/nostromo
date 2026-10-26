# Owner-only routine deployment

One authenticated setup installs a root-owned `/usr/local/sbin/nostromo-deploy` and this
command-specific sudo rule for the existing broker owner (currently `jladd`):

```sudoers
jladd ALL=(root) NOPASSWD: NOSETENV: /usr/local/sbin/nostromo-deploy
```

No crew account receives this grant. Deployment authority includes changing application code
that uses the broker's existing credentials and the workers' existing role permissions. Treat
it as owner-level control of Nostromo. It does not authorize a general root shell or installer.
The helper itself, its root configuration, service definitions, entry points, polkit rules,
accounts, and credentials cannot be changed through the routine release format.

## One-time setup on Spark

First install the campaign infrastructure using its authenticated installer. Use the release
builder's `--bootstrap-output NEW_PRIVATE_DIRECTORY` option to create a private snapshot of
the setup/helper and protected source files from the exact reviewed commit. Transfer that
directory into `/home/jladd/.config/nostromo-deploy/` with owner-only permissions. Then run:

```bash
sudo /usr/bin/python3 -I /home/jladd/.config/nostromo-deploy/bootstrap-COMMIT/infrastructure/spark/bin/install-nostromo-deploy.py
```

The shared `nostromo`-owned checkout must not be used as the root setup source: another
account could change it while the owner enters a password. The installer requires a private
owner/root-owned, non-symlink source path. Setup derives the human owner from the existing
root-owned broker configuration. It checks
service identities, `NoNewPrivileges`, capabilities, root ownership, and privileged hook
prefixes; pins installed unit/entry-point bytes; and proves the owner's socket access. It
validates the sudo rule with `visudo` before installing it. It creates a private root-owned
state directory, configuration, and deployment lock. The setup grants no new crew permission.
It refuses unsupported unit drop-ins and unresolved interrupted deployments.

The installed helper uses isolated Python and only the standard library. It never imports
application modules or executes Git, repository installers, build hooks, or release code as root.
The only application probe runs as the existing owner UID with socket-group access and makes
the fixed read-only `shared-ready` request. Root subprocesses are fixed systemctl operations.

## Routine updates

Commit and test changes first. Mirror the committed source with the existing `push-repo.sh`
workflow; that source mirror continues to supply harness prompts at the next turn. Build a
release as the unprivileged owner, never with sudo:

```bash
python3 -I infrastructure/spark/bin/deploy-release.py \
  --commit FULL_FORTY_CHARACTER_COMMIT --output /private/tmp/nostromo-release.json
```

This reads tracked regular blobs from the exact commit; uncommitted files do not travel.
Its JSON result gives the SHA-256 of the complete release bytes. Transfer that file over the
existing owner SSH connection to a private file on Spark, then run:

```bash
sudo -n /usr/local/sbin/nostromo-deploy apply FULL_FORTY_CHARACTER_COMMIT RELEASE_SHA256 \
  < /home/jladd/.config/nostromo-deploy/release.json
sudo -n /usr/local/sbin/nostromo-deploy status
```

The commit is owner-supplied release attribution; the bundle hash proves the installed bytes,
not a GitHub approval or test result. The release builder reads that exact Git commit and the
owner remains responsible for authorizing and testing it. The privileged helper validates the
checksum, complete file inventory, size bounds, and pinned infrastructure before any update.

Allowed content is flat Python modules under `runtime/campaigns`, the existing Nostr helper,
the campaign/shared-inference/deployment runbooks, and Ripley/Dallas campaign personas. Entry points,
service units, polkit rules, and the crew manifest must match the bootstrapped source pins.
Updating any of those requires authenticated infrastructure/setup work. Inputs cannot name
arbitrary destination paths, links, helper updates, credentials, or service configuration.

The helper serializes updates, saves the current code privately, pauses only previously active
campaign timers, and refuses an active campaign worker service without killing it. It stops
the broker/watcher for replacement, restarts them, verifies their health and role-authenticated
socket access, and restores the previous timer state. It does not enable disabled timers,
restart crew harnesses or TensorFold, or request a campaign or provider call. Control polling
is briefly unavailable during deployment; use an appropriate campaign boundary.

Health/copy failure restores the previous code and checks it before restoring timers. The
private current record and backup chain retain commit IDs and exact file hashes. Reapplying
the identical installed release is a health-checked no-op. Rollback is code-only: it never
restores or rewinds campaign state, keys, budgets, or provider reservations. Releases must keep
stored-state changes backward compatible; incompatible migrations require attended maintenance.

## Interrupted deployment and revocation

`status` reports `files_match`, unit states, and an `interrupted` marker. If the helper is killed,
rollback cannot be verified, or timer restoration fails, `pending.json` remains in
`/var/lib/nostromo-deploy`. A new routine deployment refuses to continue. Timers may be stopped;
inspect the saved backup and actual unit states as the authenticated owner before restoring code
or resuming services. Never clear the marker just to force another update.

To revoke password-free deployment, remove `/etc/sudoers.d/nostromo-deploy` as authenticated
root and run `visudo -c`. The application continues running; removal only revokes the grant.
Changing the helper or its allowed infrastructure requires another reviewed, authenticated setup.
