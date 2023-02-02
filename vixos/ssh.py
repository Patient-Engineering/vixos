from pathlib import Path
from Crypto.PublicKey import RSA
import subprocess
import paramiko


class SshManager:
    def __init__(self, vixos_path: Path) -> None:
        self.vixos_path = vixos_path
        self.privkey_path = self.vixos_path / "vixos_id_rsa"
        self.privkey = self.ensure_privkey()

    def ensure_privkey(self) -> RSA.RsaKey:
        if not self.privkey_path.exists():
            key = RSA.generate(2048)
            self.privkey_path.write_bytes(key.exportKey("PEM"))

        return RSA.importKey(self.privkey_path.read_bytes())

    @property
    def pubkey_text(self) -> str:
        return self.privkey.publickey().exportKey("OpenSSH").decode()

    def interactive_session(self, user: str, host: str) -> None:
        # TODO: use a hardcoded known host key here instead?
        # TODO: use paramiko session instead of shelling to ssh?
        subprocess.check_call(
            [
                "ssh",
                f"user@{host}",
                "-i",
                str(self.privkey_path),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
            ]
        )

    def ssh_session(self, user: str, host: str) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            username=user,
            hostname=host,
            key_filename=str(self.privkey_path),
        )
        return ssh

    def get_from_remote(
        self, user: str, host: str, remote_path: str, local_path: str
    ) -> None:
        ssh = self.ssh_session(user, host)
        with ssh.open_sftp() as sftp:
            sftp.get(remote_path, local_path)

    def put_in_remote(
        self, user: str, host: str, remote_path: str, local_path: str
    ) -> None:
        ssh = self.ssh_session(user, host)
        with ssh.open_sftp() as sftp:
            sftp.put(remote_path, local_path)
