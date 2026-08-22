#!/usr/bin/env python3
"""Phase 0.3 smoke test — verify the two agent -> kali channels.

Run from INSIDE the agent container:

    docker exec agent python /app/docker/agent/smoke_channels.py

Channel policy (SSH vs msfrpc), by action type:
  - SSH (paramiko / ssh)  -> arbitrary tools: nmap, enumeration, custom shell commands.
                             The agent shells into kali-tools and runs the tool there;
                             raw stdout is the observation O fed to the Belief Updater.
  - msfrpc (pymetasploit3) -> Metasploit exploit modules. Driving Metasploit over its RPC
                             API is cleaner and more robust than screen-scraping msfconsole
                             over SSH, so exploit/lateral/privesc actions that use MSF modules
                             go through this channel.

Both channels live ONLY on the isolated labnet; kali-tools has no internet route.
Secrets come from the environment (.env), never hard-coded.
"""
import os
import subprocess
import sys

KALI_HOST = os.environ.get("KALI_HOST", "kali-tools")
TARGET = os.environ.get("SMOKE_TARGET", "target")
SSH_KEY = os.environ.get("AGENT_SSH_KEY", "/root/.ssh/id_ed25519")
MSF_PORT = int(os.environ.get("MSF_RPC_PORT", "55553"))
MSF_PASSWORD = os.environ.get("MSF_RPC_PASSWORD", "")


def ssh_channel() -> str:
    """SSH into kali-tools and run nmap against the target; return raw output O."""
    # Bind-mounted key can carry loose perms; copy to a private path so ssh accepts it.
    key = "/tmp/agent_key"
    subprocess.run(["cp", SSH_KEY, key], check=True)
    os.chmod(key, 0o600)
    cmd = [
        "ssh", "-i", key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=15",
        f"root@{KALI_HOST}",
        f"nmap -Pn -T4 {TARGET}",
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return (out.stdout + out.stderr).strip()


def msfrpc_channel() -> int:
    """Connect to msfrpcd on kali-tools and return the number of exploit modules."""
    from pymetasploit3.msfrpc import MsfRpcClient  # imported lazily so SSH test can run alone
    if not MSF_PASSWORD:
        raise RuntimeError("MSF_RPC_PASSWORD not set in environment (.env)")
    client = MsfRpcClient(MSF_PASSWORD, server=KALI_HOST, port=MSF_PORT, ssl=False)
    return len(client.modules.exploits)


def main() -> int:
    rc = 0

    print("=" * 70)
    print("[SSH] agent -> kali-tools -> nmap", TARGET)
    print("=" * 70)
    try:
        o = ssh_channel()
        print(o[:2000])
        if "Nmap scan report" in o or "Host is up" in o or "Nmap done" in o:
            print("\n[SSH] OK — captured observation O from a real tool run.")
        else:
            print("\n[SSH] WARN — ran but did not recognize nmap output; inspect above.")
            rc = 1
    except Exception as e:  # noqa: BLE001 - smoke test surfaces any failure
        print(f"[SSH] FAIL: {e}")
        rc = 1

    print("\n" + "=" * 70)
    print(f"[MSFRPC] agent -> kali-tools:{MSF_PORT} (pymetasploit3)")
    print("=" * 70)
    try:
        n = msfrpc_channel()
        print(f"[MSFRPC] OK — msfrpcd reachable; {n} exploit modules listed.")
    except Exception as e:  # noqa: BLE001
        print(f"[MSFRPC] FAIL: {e}")
        rc = 1

    print("\nRESULT:", "PASS" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
