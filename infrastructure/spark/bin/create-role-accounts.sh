#!/usr/bin/env bash
# Give every crew role its own Unix account on the Spark.
#
# WHY. Until now all seven agents shared one account, which made every per-role control advisory.
# An agent could read any other role's GitHub App key and mint that role's token, read any other
# role's provider key and spend its budget, read any other role's Buzz key and post as that crew
# member, inspect or kill another agent's process, and edit the permission profiles and credential
# helpers meant to constrain it. The design's own rule is that deterministic controls beat prompt
# promises; a boundary every agent can step over is a prompt promise.
#
# This matters beyond security. If Parker can act as Dallas then "Dallas reviewed this" stops being
# evidence of independent review, and NOSTROMO-0002's whole measurement apparatus rests on
# attribution being real.
#
# WHAT THIS DOES NOT CHANGE. An agent can still do anything its own role permits — that is the
# design. Network access stays unrestricted. The launcher must still be trusted, since it holds
# every key in order to hand each role only its own.
#
# Run ON the Spark, as root:  sudo bash create-role-accounts.sh
# Idempotent. Grants no sudo and no docker to anyone.
set -euo pipefail

ROLES=(mother ash ripley dallas parker brett lambert)
SUPERVISOR="${SUPERVISOR:-nostromo}"      # owns the shared runtime and runs the launcher
OWNER="${OWNER:-jladd}"
RUNTIME_ROOT="${RUNTIME_ROOT:-/opt/nostromo}"

[[ "$(id -u)" == "0" ]] || { echo "run as root: sudo bash $0" >&2; exit 1; }
id "$SUPERVISOR" >/dev/null 2>&1 || { echo "supervisor account $SUPERVISOR does not exist; run create-crew-user.sh first" >&2; exit 1; }

say() { printf '==> %s\n' "$*"; }

# The shared group is the existing supervisor's primary group. It carries crew affiliation and
# grants read of the shared runtime — nothing else. Crew files never rely on it.
say "using group '$SUPERVISOR' for crew affiliation and runtime read"

for role in "${ROLES[@]}"; do
  if id "$role" >/dev/null 2>&1; then
    say "$role exists"
  else
    say "creating $role"
    # No colon in the comment: /etc/passwd is colon-delimited and useradd rejects it.
    useradd --create-home --shell /bin/bash --groups "$SUPERVISOR" \
            --comment "Nostromo crew $role" "$role"
  fi

  # 700, NOT 750. With a shared group, 750 would let every role read every other role's home and
  # reintroduce exactly the problem this script exists to solve.
  chmod 700 "/home/$role"
  # install -d applies -o/-g only to the FINAL directory, so the intermediate ones were left
  # owned by root and the role could not create anything beside `secrets`. Create each level.
  for d in ".config" ".config/nostromo" ".config/nostromo/secrets"; do
    install -d -m 700 -o "$role" -g "$role" "/home/$role/$d"
  done
  chown -R "$role:$role" "/home/$role/.config/nostromo"

  # Refuse to leave a role holding an escalation.
  for forbidden in sudo docker adm; do
    if id -nG "$role" | tr ' ' '\n' | grep -qx "$forbidden"; then
      echo "REFUSING: $role is in group '$forbidden'" >&2
      echo "remove it with: sudo gpasswd -d $role $forbidden" >&2
      exit 1
    fi
  done

  # The owner's key, so each account can be inspected and its boundary verified from inside it.
  if [[ -s "/home/$OWNER/.ssh/authorized_keys" ]]; then
    install -d -m 700 -o "$role" -g "$role" "/home/$role/.ssh"
    install -m 600 -o "$role" -g "$role" \
      "/home/$OWNER/.ssh/authorized_keys" "/home/$role/.ssh/authorized_keys"
  fi
done

# The supervisor's secret directory was 755; the keys inside were 600, but the listing was open.
chmod 700 "/home/$SUPERVISOR/.config/nostromo/secrets" 2>/dev/null || true
chmod 700 "/home/$SUPERVISOR"

# Shared runtime: readable by the group, writable only by the supervisor.
chown -R "$SUPERVISOR:$SUPERVISOR" "$RUNTIME_ROOT"
chmod 755 "$RUNTIME_ROOT"

echo
say "accounts created. Verify from inside them, which is the position an agent occupies:"
echo "    infrastructure/spark/bin/verify-role-isolation.sh"
echo
getent group "$SUPERVISOR"
