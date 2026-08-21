#!/usr/bin/env bash
set -euo pipefail

# Install the agent's SSH public key (passed via .env) for key-based login.
if [ -n "${AGENT_SSH_PUBKEY:-}" ]; then
  mkdir -p /root/.ssh
  echo "$AGENT_SSH_PUBKEY" > /root/.ssh/authorized_keys
  chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
fi

# Start SSH daemon.
/usr/sbin/sshd

# Start the Metasploit RPC daemon so the agent can drive Metasploit over the API.
# -S = no SSL (acceptable on an ISOLATED internal network; enable SSL otherwise).
: "${MSF_RPC_PASSWORD:?set MSF_RPC_PASSWORD in .env}"
msfrpcd -P "$MSF_RPC_PASSWORD" -S -a 0.0.0.0 -p 55553 &

# Keep the container in the foreground.
tail -f /dev/null
