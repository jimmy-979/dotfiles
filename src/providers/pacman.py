from packages import package_names, run


def install(config: dict) -> None:
    run(["sudo", "pacman", "-S", "--needed", "--noconfirm", *package_names(config)])


def check(name: str) -> tuple[str | None, str | None]:
    import subprocess

    installed = subprocess.run(
        ["pacman", "-Q", name], capture_output=True, text=True, check=False
    )
    if installed.returncode != 0:
        return None, None
    fields = installed.stdout.strip().split()
    installed_version = fields[1] if len(fields) >= 2 else None
    candidate = subprocess.run(
        ["pacman", "-Si", name], capture_output=True, text=True, check=False
    )
    candidate_version = None
    for line in candidate.stdout.splitlines():
        if line.strip().startswith("Version"):
            candidate_version = line.split(":", 1)[1].strip()
            break
    return installed_version, candidate_version
