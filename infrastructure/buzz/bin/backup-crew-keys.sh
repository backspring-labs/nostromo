#!/usr/bin/env bash
# Encrypted backup of all seven crew Buzz private keys.
#
# WHY IT IS ENCRYPTED WITH AN OWNER-HELD PASSPHRASE. Each key currently lives in exactly one place:
# its own role's account on the Spark, readable by no other role. A backup must not undo that. The
# bundle is ciphertext everywhere it is stored, and the passphrase never touches the Spark — so a
# compromised crew account, or a stolen backup file, yields nothing.
#
# WHAT IT PROTECTS AGAINST, AND WHAT IT DOES NOT. Two copies land on two machines: the Spark, for
# a fast restore after a mistake, and the Mac, which is the copy that survives losing the Spark.
# Agent keys are also replaceable in a way the owner's key is not — if all seven were lost they can
# be regenerated and re-registered in minutes. What cannot be recovered is provenance: past messages
# and commits stay under the old keys. So this is about confidentiality first, recovery second.
#
# Run from the Mac. Prompts for the passphrase with no echo; it reaches no terminal, shell history
# or transcript. Store it beside the owner identity in the password manager.
set -euo pipefail

ROLES=(mother ash ripley dallas parker brett lambert)
HOST="${SPARK_HOST:-spark}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
MAC_DIR="$HOME/.nostromo/backups/crew-keys"
SPARK_DIR="/opt/nostromo/backups/crew-keys"
NAME="crew-buzz-keys-$STAMP.tar.gz.enc"

read -rsp "Passphrase for the crew key backup (input hidden): " PASS; echo
[[ ${#PASS} -ge 12 ]] || { echo "use at least 12 characters — this is the only thing protecting seven identities" >&2; exit 1; }
read -rsp "Again: " PASS2; echo
[[ "$PASS" == "$PASS2" ]] || { echo "passphrases do not match" >&2; exit 1; }

# Collect each key by ssh'ing AS that role, so no single account ever holds all seven on disk.
# The plaintext exists only in this process's memory and a 700 temp directory on the Mac.
TMP="$(mktemp -d)"; chmod 700 "$TMP"
trap 'rm -rf "$TMP"; unset PASS PASS2' EXIT

echo "==> collecting"
for role in "${ROLES[@]}"; do
  key="$(ssh -n "$role@$HOST" 'cat ~/.config/nostromo/secrets/buzz.key')"
  [[ ${#key} -eq 64 ]] || { echo "  $role: expected 64 hex chars, got ${#key}" >&2; exit 1; }
  printf '%s' "$key" > "$TMP/$role.key"
  pub="$(ssh -n "$role@$HOST" 'cat ~/.config/nostromo/secrets/buzz.pubkey')"
  printf '  %-8s %s\n' "$role" "$pub"
done
cp crew/manifest.yaml "$TMP/manifest.yaml"   # so a restorer knows which key is whose

echo "==> encrypting (AES-256, PBKDF2, 600k iterations)"
# -pass fd:3 rather than env:PASS. Exporting the passphrase would put it in this process's
# environment, readable through /proc by anything running as the same user; a file descriptor is
# private to the process and never lands in a variable openssl can be asked to read.
tar -czf - -C "$TMP" . | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt \
  -pass fd:3 -out "$TMP/$NAME" 3<<<"$PASS"

# Prove it decrypts before distributing it. An unverified backup is a guess.
echo "==> verifying the bundle decrypts and contains seven keys"
n=$(openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass fd:3 -in "$TMP/$NAME" 3<<<"$PASS" \
     | tar -tzf - | grep -c '\.key$')
[[ "$n" -eq 7 ]] || { echo "verification failed: found $n keys, expected 7" >&2; exit 1; }
echo "    7 keys, round trip verified"

mkdir -p "$MAC_DIR"; install -m 600 "$TMP/$NAME" "$MAC_DIR/$NAME"
ssh "$HOST" "mkdir -p $SPARK_DIR && chmod 755 $SPARK_DIR" 2>/dev/null || true
scp -q "$TMP/$NAME" "nostromo@$HOST:$SPARK_DIR/$NAME"
ssh -n "nostromo@$HOST" "chmod 600 $SPARK_DIR/$NAME"

echo "==> stored"
echo "    Mac    $MAC_DIR/$NAME"
echo "    Spark  $SPARK_DIR/$NAME"
echo
echo "Put the passphrase in your password manager beside the owner identity. Without it this"
echo "bundle is unopenable, and there is no other copy of these keys."
