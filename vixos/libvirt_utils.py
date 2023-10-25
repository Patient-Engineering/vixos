import libvirt
from contextlib import contextmanager
from typing import Any


@contextmanager
def libvirt_connection(uri: str) -> Any:
    conn = libvirt.open(uri)
    if not conn:
        raise RuntimeError(f"Failed to open connection to {uri}")
    try:
        yield conn
    finally:
        conn.close()
