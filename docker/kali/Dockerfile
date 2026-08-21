FROM kalilinux/kali-rolling

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
