from packages import command_exists, package_names, run


def install(config: dict) -> None:
    if not command_exists("yay"):
        raise RuntimeError("AUR provider requires 'yay', but yay is not installed")
    run(["yay", "-S", "--needed", "--noconfirm", *package_names(config)])


check = None
