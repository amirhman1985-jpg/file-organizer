from pathlib import Path
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


KEYS_DIR = Path("keys")


def main() -> None:
    KEYS_DIR.mkdir(exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    (KEYS_DIR / "license_private.key").write_bytes(
        private_bytes
    )

    (KEYS_DIR / "license_public.key").write_bytes(
        base64.b64encode(public_bytes)
    )

    print("License keys generated.")


if __name__ == "__main__":
    main()