#!/usr/bin/env bash
# Installs and starts the systemd user service, substituting the repository's actual path on the target machine.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$UNIT_DIR"

sed "s|%h/EmbeddedResearcher|$REPO_DIR|g" "$REPO_DIR/deploy/unitn-net.service" > "$UNIT_DIR/unitn-net.service"
echo "Wrote $UNIT_DIR/unitn-net.service (WorkingDirectory=$REPO_DIR)"

systemctl --user daemon-reload
systemctl --user enable --now unitn-net
systemctl --user status unitn-net --no-pager
