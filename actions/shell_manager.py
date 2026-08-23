import os

import paramiko

from actions.remote_shell import RemoteShell
from config.config import Configs


class ShellManager:
    _instance = None
    _ssh_client = None
    _shell = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_shell(self) -> RemoteShell:
        if self._shell is None:
            self._connect()
        return self._shell

    def _connect(self):
        if self._ssh_client is None:
            kali = Configs.basic_config.kali
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connect_kwargs = dict(
                hostname=kali['hostname'],
                username=kali['username'],
                port=kali['port'],
            )
            # Prefer key auth when a key path is configured + present (docker lab: kali trusts the
            # agent key, sshd is key-only). Otherwise fall back to password auth (remote Kali VM).
            key_filename = kali.get('key_filename') or ''
            key_path = os.path.abspath(key_filename) if key_filename else ''
            if key_path and os.path.isfile(key_path):
                connect_kwargs['key_filename'] = key_path
            else:
                connect_kwargs['password'] = kali.get('password') or ''
            self._ssh_client.connect(**connect_kwargs)
        if self._shell is None:
            self._shell = RemoteShell(self._ssh_client.invoke_shell())

    def close(self):
        if self._shell:
            try:
                self._shell.shell.close()
            except:
                pass
            self._shell = None

        if self._ssh_client:
            try:
                self._ssh_client.close()
            except:
                pass
            self._ssh_client = None