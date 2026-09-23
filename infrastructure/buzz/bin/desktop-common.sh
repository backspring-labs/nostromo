# Shared by the Buzz Desktop scripts on the owner's Mac. Sourced, not run.
#
# One definition of "Buzz is running". The previous one looked for a process named `Buzz`, but the
# binary is Contents/MacOS/buzz-desktop and pgrep is case-sensitive, so it never matched: measured
# 2026-09-23 with Buzz open, purge-desktop-agents.sh would have rewritten the app's files underneath
# it. Match the bundle path instead. It also catches the agent processes the app spawns from the
# bundle (buzz-acp, buzz-agent), which must be gone too before anything touches the app's files.

BUZZ_BUNDLE_ID=xyz.block.buzz.app
BUZZ_APP=/Applications/Buzz.app
BUZZ_SUPPORT="$HOME/Library/Application Support/$BUZZ_BUNDLE_ID"
# Browser storage. Holds buzz-welcome-channel-ensured.v2, the flag that stops the Welcome team being
# provisioned again, so a backup or rollback that leaves this out can bring the default agents back.
BUZZ_WEBKIT="$HOME/Library/WebKit/$BUZZ_BUNDLE_ID"
BUZZ_RUNNING_RE='^/Applications/Buzz\.app/Contents/MacOS/'

buzz_running() { pgrep -qf "$BUZZ_RUNNING_RE"; }
