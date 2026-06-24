"""Local gateway injection control socket helpers."""

from __future__ import annotations

import json
import os
import socket
import stat
from pathlib import Path
from typing import Any

from hermes_cli.config import get_hermes_home

MAX_INJECT_BYTES = 256 * 1024


def inject_socket_path() -> Path:
    return get_hermes_home() / "gateway" / "inject.sock"


def ensure_private_socket_parent(path: Path | None = None) -> Path:
    path = path or inject_socket_path()
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(parent, 0o700)
    except OSError:
        pass
    return parent


def validate_socket_security(path: Path) -> tuple[bool, str]:
    """Return whether *path* is a Unix socket owned by this user and not public."""
    try:
        st = path.stat()
    except FileNotFoundError:
        return False, "Gateway inject socket not found. Is the gateway running?"
    except OSError as exc:
        return False, f"Cannot inspect gateway inject socket: {exc}"

    if not stat.S_ISSOCK(st.st_mode):
        return False, f"Gateway inject path is not a socket: {path}"
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        return False, "Gateway inject socket is owned by another user."
    if st.st_mode & 0o077:
        return False, "Gateway inject socket permissions are too broad."
    return True, ""


def dumps_request(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"


def loads_request(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_INJECT_BYTES:
        raise ValueError("inject request is too large")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid inject JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("inject request must be a JSON object")
    return payload


def send_inject_request(payload: dict[str, Any], *, timeout: float = 300.0) -> dict[str, Any]:
    if not hasattr(socket, "AF_UNIX"):
        return {"ok": False, "error": "Gateway inject is not supported on this platform."}
    path = inject_socket_path()
    ok, reason = validate_socket_security(path)
    if not ok:
        return {"ok": False, "error": reason}

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(str(path))
            sock.sendall(dumps_request(payload))
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_INJECT_BYTES:
                    return {"ok": False, "error": "inject response is too large"}
    except TimeoutError:
        return {"ok": False, "error": "Timed out waiting for gateway inject response."}
    except OSError as exc:
        return {"ok": False, "error": f"Gateway inject request failed: {exc}"}

    raw = b"".join(chunks).strip()
    if not raw:
        return {"ok": False, "error": "Gateway inject response was empty."}
    try:
        response = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"Invalid gateway inject response: {exc}"}
    if not isinstance(response, dict):
        return {"ok": False, "error": "Gateway inject response was not an object."}
    return response
