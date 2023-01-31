from pathlib import Path
from Crypto.PublicKey import RSA


class SshManager:
    def __init__(self, vixos_path: Path) -> None:
        self.vixos_path = vixos_path
        self.privkey = self.ensure_privkey()

    def ensure_privkey(self) -> RSA.RsaKey:
        privkey_path = self.vixos_path / "vixos_id_rsa"
        if not privkey_path.exists():
            key = RSA.generate(2048)
            privkey_path.write_bytes(key.exportKey("PEM"))

        return RSA.importKey(privkey_path.read_bytes())

    @property
    def pubkey_text(self) -> str:
        return self.privkey.publickey().exportKey("OpenSSH").decode()
