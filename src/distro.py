import platform
from pathlib import Path


def detect_distro() -> str:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        raise RuntimeError("Cannot find /etc/os-release")
    values = {}
    for line in os_release.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip('"')
    distro = values.get("ID")
    if distro in {"debian", "ubuntu"}:
        return "debian"
    if distro == "arch":
        return "arch"
    raise RuntimeError(f"Unsupported Linux distribution: {distro}")


def detect_arch() -> str:
    machine = platform.machine().lower()
    mapping = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armv7",
        "armv7": "armv7",
    }
    try:
        return mapping[machine]
    except KeyError:
        raise RuntimeError(f"Unsupported architecture: {machine}")
