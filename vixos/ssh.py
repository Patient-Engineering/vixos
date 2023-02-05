import os
from pathlib import Path
import select
import signal
import socket
import sys
import termios
import tty
from Crypto.PublicKey import RSA
import subprocess
import paramiko


class SshManager:
    def __init__(self, vixos_root: Path) -> None:
        self.vixos_root = vixos_root
        self.privkey_path = self.vixos_root / "vixos_id_rsa"
        self.privkey = self.ensure_privkey()

    def ensure_privkey(self) -> RSA.RsaKey:
        if not self.privkey_path.exists():
            key = RSA.generate(2048)
            self.privkey_path.write_bytes(key.exportKey("PEM"))
            self.privkey_path.chmod(0o400)

        return RSA.importKey(self.privkey_path.read_bytes())

    @property
    def pubkey_text(self) -> str:
        return self.privkey.publickey().exportKey("OpenSSH").decode()

    def interactive_session(self, user: str, host: str) -> None:
        ssh = self.ssh_session(user, host)
        width, height = os.get_terminal_size()
        shell_chan = ssh.invoke_shell(os.getenv('TERM', 'vt100'), width, height)

        def signal_handler(_signum, _frame):
            width, height = os.get_terminal_size()
            shell_chan.resize_pty(width, height)
        signal.signal(signal.SIGWINCH, signal_handler)

        tty_attr = termios.tcgetattr(sys.stdin)
        try:
            # make terminal raw, disable line buffering
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            shell_chan.settimeout(0.0)

            while True:
                read_ready, _, _ = select.select([shell_chan, sys.stdin], [], [])
                if shell_chan in read_ready:
                    try:
                        b = shell_chan.recv(1024)
                        if len(b) == 0:
                            print(f'\nConnection to {host} closed')
                            break
                        sys.stdout.buffer.write(b)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in read_ready:
                    b = sys.stdin.buffer.read(1)
                    if len(b) == 0:
                        break
                    shell_chan.send(b)
        finally:
            # restore saved tty attributes
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, tty_attr)
            # reset temporary signal handler back to SIG_DFL (default)
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)

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
