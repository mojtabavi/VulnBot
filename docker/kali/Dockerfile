FROM kalilinux/kali-rolling

# Pin apt to a reachable Kali mirror. The default round-robin (http.kali.org /
# kali.download) is Cloudflare-fronted and returns 403 from some regions/networks,
# which breaks `apt-get update`. The base image defines its repo in the deb822 file
# /etc/apt/sources.list.d/kali.sources; rewrite the URI in place (keeping the
# Signed-By keyring). Swap the host for a closer one if needed
# (see https://http.kali.org/README.mirrorlist).
ARG KALI_MIRROR_HOST=kali.mirror.rafal.ca
RUN sed -i "s#http://http.kali.org/kali/#http://${KALI_MIRROR_HOST}/kali/#" \
      /etc/apt/sources.list.d/kali.sources

# Kali containers are minimal. kali-linux-headless pulls the core toolset
# (nmap, metasploit-framework, etc.). openssh-server + net utils added for the
# agent->kali channel.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      kali-linux-headless \
      openssh-server \
      iproute2 iputils-ping netcat-traditional ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# SSH: key-based only
RUN mkdir -p /run/sshd && \
    sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 22 55553
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
