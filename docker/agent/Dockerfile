FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      git openssh-client build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install VulnBot's own requirements if present, then the clients the belief
# agent needs to reach kali (msfrpc + ssh).
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir pymetasploit3 paramiko

# Repo is mounted at runtime via the compose volume.
