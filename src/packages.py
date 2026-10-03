from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LOCAL_BIN = Path.home() / ".local" / "bin"
LOCAL_OPT = Path.home() / ".local" / "opt"


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    @classmethod
    def enabled(cls) -> bool:
        return (
            sys.stdout.isatty()
            and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb"
        )

    @classmethod
    def wrap(cls, text: str, color: str) -> str:
        return f"{color}{text}{cls.RESET}" if cls.enabled() else text


def pkg_print(
    message: str = "", *, color: str = Colors.CYAN, bold: bool = False
) -> None:
    text = f"pkg: {message}"
    if bold and Colors.enabled():
        text = f"{Colors.BOLD}{text}{Colors.RESET}"
    if color:
        text = Colors.wrap(text, color)
    print(text)


def pkg_error(message: str) -> None:
    text = f"pkg: error: {message}"
    if Colors.enabled():
        text = Colors.wrap(text, Colors.RED)
    print(text, file=sys.stderr)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    pkg_print(f"$ {' '.join(cmd)}", color=Colors.BLUE, bold=True)
    return subprocess.run(cmd, check=check, text=True)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def command_version(command: str) -> str | None:
    for args in (["--version"], ["-version"], ["version"]):
        try:
            result = subprocess.run(
                [command, *args], capture_output=True, text=True, check=False
            )
        except OSError:
            continue
        output = (result.stdout or result.stderr).strip()
        if output:
            return output.splitlines()[0].strip()
    return None


def package_names(config: dict) -> list[str]:
    names = config.get("name")
    if isinstance(names, str):
        return [names]
    if isinstance(names, list) and all(
        isinstance(name, str) and name for name in names
    ):
        return names
    raise RuntimeError("'name' must be a string or a non-empty list of strings")


def normalize_version(version: str) -> tuple:
    value = re.sub(r"^[vV]", "", version.strip())
    parts = re.findall(r"\d+|[A-Za-z]+", value)
    return tuple((0, int(p)) if p.isdigit() else (1, p.lower()) for p in parts)


def versions_differ(installed: str, latest: str) -> bool:
    return normalize_version(installed) != normalize_version(latest)


def install_package(package_name: str, package: dict, distro: str, arch: str) -> None:
    config = package.get(distro)
    if config is None:
        raise RuntimeError(f"{package_name}: no configuration for distro {distro!r}")
    provider = config.get("provider")
    if not provider:
        raise RuntimeError(f"{package_name}: provider is missing for distro {distro!r}")
    pkg_print()
    pkg_print(
        f"==> {package_name} [{distro}/{provider}]",
        color=Colors.MAGENTA,
        bold=True,
    )
    if provider == "apt":
        from providers import apt

        apt.install(config)
    elif provider == "pacman":
        from providers import pacman

        pacman.install(config)
    elif provider == "aur":
        from providers import aur

        aur.install(config)
    elif provider == "github":
        from providers import github

        typ = config.get("type")
        if typ == "appimage":
            github.install_appimage(package_name, package["command"], config, arch)
        elif typ == "archive":
            github.install_archive(package_name, config, arch)
        else:
            raise RuntimeError(f"{package_name}: unsupported GitHub type {typ!r}")
    else:
        raise RuntimeError(f"{package_name}: unknown provider {provider!r}")


def check_packages(packages: dict, distro: str) -> bool:
    from providers import apt, github, pacman

    success = True
    pkg_print()
    pkg_print(
        f"{'Package':<20} {'Installed':<24} {'Available':<24} Status", color=Colors.BOLD
    )
    pkg_print(f"{'-' * 20} {'-' * 24} {'-' * 24} {'-' * 12}", color=Colors.DIM)
    for name, package in packages.items():
        command = package.get("command")
        config = package.get(distro, {})
        provider = config.get("provider")
        if command:
            if not command_exists(command):
                pkg_print(
                    f"{name:<20} {'not installed':<24} {'-':<24} [MISSING]",
                    color=Colors.RED,
                )
                success = False
                continue
            installed_version = available_version = None
            try:
                if provider == "github" and config.get("type") == "appimage":
                    installed_version = github.installed_version(name)
                    available_version = github.release_version(config["repo"])
                elif provider == "apt":
                    names = package_names(config)
                    if len(names) == 1:
                        installed_version, available_version = apt.check(names[0])
                elif provider in {"pacman", "aur"}:
                    names = package_names(config)
                    if len(names) == 1:
                        installed_version, available_version = pacman.check(names[0])
                if installed_version is None:
                    installed_version = command_version(command)
            except Exception as exc:
                pkg_print(f"{name}: version check failed: {exc}", color=Colors.YELLOW)
            installed_display = installed_version or "unknown"
            available_display = available_version or "unknown"
            update = (
                installed_version
                and available_version
                and versions_differ(installed_version, available_version)
            )
            status = "[UPDATE]" if update else "[ OK ]"
            color = Colors.YELLOW if update else Colors.GREEN
            pkg_print(
                f"{name:<20} {installed_display:<24} {available_display:<24} {status}",
                color=color,
            )
            continue
        try:
            names = package_names(config)
        except Exception as exc:
            pkg_print(f"{name}: package check failed: {exc}", color=Colors.RED)
            success = False
            continue
        for package_name in names:
            try:
                if provider == "apt":
                    installed_version, available_version = apt.check(package_name)
                elif provider in {"pacman", "aur"}:
                    installed_version, available_version = pacman.check(package_name)
                else:
                    raise RuntimeError(f"unsupported provider {provider!r}")
            except Exception as exc:
                pkg_print(
                    f"{name}/{package_name}: version check failed: {exc}",
                    color=Colors.YELLOW,
                )
                installed_version = available_version = None
            if installed_version is None:
                pkg_print(
                    f"{name}/{package_name:<15} {'not installed':<24} {'-':<24} [MISSING]",
                    color=Colors.RED,
                )
                success = False
                continue
            update = bool(
                available_version
                and versions_differ(installed_version, available_version)
            )
            status = "[UPDATE]" if update else "[ OK ]"
            color = Colors.YELLOW if update else Colors.GREEN
            pkg_print(
                f"{name}/{package_name:<15} {installed_version:<24} {(available_version or 'unknown'):<24} {status}",
                color=color,
            )
    pkg_print()
    return success
