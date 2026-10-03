import argparse

from config_linker import configure_package
from distro import detect_arch, detect_distro
from packages import Colors, check_packages, install_package, pkg_print
from src.config import load_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkg",
        description="Cross-distro package manager for dotfiles",
    )
    subparsers = parser.add_subparsers(
        dest="action",
        required=True,
    )
    install_parser = subparsers.add_parser(
        "install",
        help="Install packages",
    )
    install_parser.add_argument(
        "packages",
        nargs="*",
        help="Packages to install. If omitted, install everything.",
    )
    subparsers.add_parser(
        "check",
        help="Check installed packages",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest = load_manifest()
    packages = manifest.get("packages")
    if not isinstance(packages, dict):
        raise TypeError("packages.toml does not contain a [packages.*] section")
    distro = detect_distro()
    arch = detect_arch()
    pkg_print(f"Distribution : {distro}", color=Colors.CYAN)
    pkg_print(f"Architecture : {arch}", color=Colors.CYAN)
    if args.action == "check":
        return 0 if check_packages(packages, distro) else 1
    if args.action == "install":
        names = args.packages or list(packages.keys())
        for name in names:
            if name not in packages:
                raise RuntimeError(f"Unknown package: {name}")
            install_package(name, packages[name], distro, arch)
            configure_package(name, packages[name])
        pkg_print()
        pkg_print("Installation complete", color=Colors.GREEN, bold=True)
        return 0
    raise RuntimeError(f"Unknown action: {args.action}")


def run_cli() -> None:
    main()
