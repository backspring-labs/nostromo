#!/usr/bin/env bash
# Create the unprivileged Unix account the Nostromo crew runs as, on the Spark.
#
# WHY THIS EXISTS. The Spark is both the owner's SquadOps workstation and the crew's execution
# host. The owner's account holds an SSH key with push access to squad-ops, a gh token with `repo`
# scope, and membership of the `docker` group, which is root-equivalent. An agent running as that
# account can push to any branch as the owner — and the crew check only fires on `nostromo/<role>/**`
# heads — can merge its own pull request, and can read every other role's credentials. Every control
# WP-1 established holds only while the crew cannot reach the owner's credentials. A separate
# account is what makes that true, and it is a filesystem boundary rather than a harness setting.
#
# Run ON the Spark, as root: sudo bash create-crew-user.sh
# Idempotent. Grants no sudo and no docker. Verifies the boundary rather than assuming it.
set -euo pipefail

CREW_USER="${CREW_USER:-nostromo}"
OWNER="${OWNER:-jladd}"
RUNTIME_ROOT="${RUNTIME_ROOT:-/opt/nostromo}"

[[ "$(id -u)" == "0" ]] || { echo "run as root: sudo bash $0" >&2; exit 1; }
id "$OWNER" >/dev/null 2>&1 || { echo "owner account $OWNER does not exist" >&2; exit 1; }

say() { printf '==> %s\n' "$*"; }

# --- the account ------------------------------------------------------------------------------
if id "$CREW_USER" >/dev/null 2>&1; then
  say "$CREW_USER already exists"
else
  say "creating $CREW_USER"
  useradd --create-home --shell /bin/bash --comment "Nostromo crew" "$CREW_USER"
fi

# Deliberately NOT added to: sudo, docker, ollama. Ollama is reached over HTTP and needs no group.
for forbidden in sudo docker adm; do
  if id -nG "$CREW_USER" | tr ' ' '\n' | grep -qx "$forbidden"; then
    echo "REFUSING: $CREW_USER is in group '$forbidden', which defeats the point of this account" >&2
    echo "remove it with: sudo gpasswd -d $CREW_USER $forbidden" >&2
    exit 1
  fi
done

# The crew's home is not world-readable, and neither is the owner's.
chmod 750 "/home/$CREW_USER"
chmod 750 "/home/$OWNER"

# --- owner's SSH access to the crew account ----------------------------------------------------
# The same key the owner already uses to reach this box, so `ssh nostromo@spark` works from the Mac
# and Herdr can be attached without a password.
if [[ -s "/home/$OWNER/.ssh/authorized_keys" ]]; then
  install -d -m 700 -o "$CREW_USER" -g "$CREW_USER" "/home/$CREW_USER/.ssh"
  install -m 600 -o "$CREW_USER" -g "$CREW_USER" \
    "/home/$OWNER/.ssh/authorized_keys" "/home/$CREW_USER/.ssh/authorized_keys"
  say "owner's authorized_keys copied to $CREW_USER"
else
  echo "WARNING: /home/$OWNER/.ssh/authorized_keys is missing or empty; you will not be able to" >&2
  echo "         ssh $CREW_USER@spark from the Mac until you add a key there." >&2
fi

# --- shared runtime root -----------------------------------------------------------------------
# World-readable on purpose: if the crew is later split into one account per role (see below), each
# role reads the same runtime instead of installing its own copy.
install -d -m 755 -o "$CREW_USER" -g "$CREW_USER" "$RUNTIME_ROOT"
say "runtime root $RUNTIME_ROOT owned by $CREW_USER, mode 755"

# --- verification ------------------------------------------------------------------------------
# Deliberately NOT duplicated here. verify-crew-boundary.sh owns the checks and runs AS the crew
# user, which is the position an agent actually occupies; root simulating that position is a
# weaker test. An earlier version of this script carried its own copy of the checks, compared the
# result against the wrong string, and reported a boundary that was holding as eight failures.
# One fact, one owner.
echo
say "account created. Now verify it, from the Mac:"
echo "    ssh $CREW_USER@spark 'bash -s' < infrastructure/spark/bin/verify-crew-boundary.sh"

cat <<EOF

Next, from the Mac:   ssh $CREW_USER@spark
Then install the runtime as $CREW_USER with NOSTROMO_RUNTIME=$RUNTIME_ROOT/runtime.

Still open, and deliberately not decided here: whether each ROLE gets its own account.
One crew account stops the crew reaching the OWNER's credentials, which is the large win.
It does not stop Parker reading Dallas's App key and approving Parker's own pull request,
which would defeat the independence model one layer down. $RUNTIME_ROOT is world-readable
so that splitting later costs a useradd and a worktree move, not a reinstall.
EOF
