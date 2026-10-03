from packages import package_names, run


def install(config: dict) -> None:
    run(["sudo", "apt-get", "install", "-y", *package_names(config)])


def check(name: str) -> tuple[str | None, str | None]:
    import subprocess

    installed = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", name],
        capture_output=True,
        text=True,
        check=False,
    )
    if installed.returncode != 0:
        return None, None
    installed_version = installed.stdout.strip() or None
    candidate = subprocess.run(
        ["apt-cache", "policy", name], capture_output=True, text=True, check=False
    )
    candidate_version = None
    for line in candidate.stdout.splitlines():
        if line.strip().startswith("Candidate:"):
            candidate_version = line.split(":", 1)[1].strip()
            break
    return installed_version, candidate_version
