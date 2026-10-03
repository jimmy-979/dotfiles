import json
import re
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

from packages import LOCAL_BIN, LOCAL_OPT, Colors, pkg_print

LOCAL_LIB = Path.home() / ".local" / "lib"
LOCAL_LIBEXEC = Path.home() / ".local" / "libexec"


def latest_release(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "dotfiles-pkg",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            data = response.read()
    except Exception as exc:
        raise RuntimeError(f"Failed to query GitHub release for {repo}: {exc}") from exc

    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned by GitHub for {repo}") from exc


def find_asset(release: dict, pattern: str) -> dict:
    for asset in release.get("assets", []):
        if re.fullmatch(pattern, asset.get("name", "")):
            return asset

    raise RuntimeError(f"No GitHub release asset matches regex: {pattern}")


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pkg_print(
        f"Downloading {url}",
        color=Colors.YELLOW,
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dotfiles-pkg"},
    )

    try:
        with (
            urllib.request.urlopen(request) as response,
            destination.open("wb") as f,
        ):
            shutil.copyfileobj(response, f)

    except Exception as exc:
        if destination.exists():
            destination.unlink()

        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def find_archive_root(
    version_root: Path,
    binary_dir: str,
) -> Path:
    """
    Find the root directory of an extracted archive.

    Supports archives that extract directly into version_root:

        version_root/
        └── bin/

    and archives with a single top-level directory:

        version_root/
        └── package-version/
            └── bin/
    """

    direct_binary_root = version_root / binary_dir

    if direct_binary_root.is_dir():
        return version_root

    directories = [entry for entry in version_root.iterdir() if entry.is_dir()]

    if len(directories) == 1:
        nested_binary_root = directories[0] / binary_dir

        if nested_binary_root.is_dir():
            return directories[0]

    return version_root


def replace_symlink(
    destination: Path,
    source: Path,
) -> None:
    """
    Create a symlink at destination pointing to source.

    Existing symlinks are replaced.

    Existing real files/directories are never replaced.
    """

    if destination.exists() or destination.is_symlink():
        if not destination.is_symlink():
            raise RuntimeError(f"Refusing to replace non-symlink: {destination}")

        destination.unlink()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.symlink_to(source)


def install_appimage(
    package_name: str,
    command: str,
    config: dict,
    arch: str,
) -> None:
    repo = config["repo"]
    assets = config["assets"]

    if arch not in assets:
        raise RuntimeError(
            f"{package_name}: no GitHub asset configured for architecture {arch!r}"
        )

    asset_config = assets[arch]
    asset_pattern = asset_config["name"]
    binary_name = asset_config.get(
        "binary",
        command,
    )

    pkg_print(
        f"Checking GitHub release: {repo}",
        color=Colors.YELLOW,
    )

    release = latest_release(repo)

    tag = release.get("tag_name")

    if not tag:
        raise RuntimeError(f"{package_name}: GitHub release has no tag_name")

    asset = find_asset(
        release,
        asset_pattern,
    )

    asset_name = asset["name"]
    download_url = asset["browser_download_url"]

    package_root = LOCAL_OPT / package_name
    version_root = package_root / tag
    executable = version_root / binary_name

    current_link = package_root / "current"
    command_link = LOCAL_BIN / command

    LOCAL_BIN.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not executable.exists():
        version_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        download_path = version_root / asset_name

        if not download_path.exists():
            download_file(
                download_url,
                download_path,
            )

        if download_path != executable:
            download_path.rename(executable)

        executable.chmod(executable.stat().st_mode | 0o111)

        pkg_print(
            f"Installed {package_name} {tag}",
            color=Colors.GREEN,
            bold=True,
        )

    else:
        pkg_print(
            f"{package_name} {tag} is already installed",
            color=Colors.GREEN,
        )

    if current_link.exists() or current_link.is_symlink():
        if not current_link.is_symlink():
            raise RuntimeError(f"Refusing to replace non-symlink: {current_link}")

        current_link.unlink()

    current_link.symlink_to(tag)

    if command_link.exists() or command_link.is_symlink():
        if not command_link.is_symlink():
            raise RuntimeError(f"Refusing to replace non-symlink: {command_link}")

        command_link.unlink()

    command_link.symlink_to(current_link / binary_name)

    pkg_print(
        f"Linked {command_link} -> {command_link.resolve()}",
        color=Colors.GREEN,
    )


def install_archive(
    package_name: str,
    config: dict,
    arch: str,
) -> None:
    repo = config["repo"]
    assets = config["assets"]

    if arch not in assets:
        raise RuntimeError(
            f"{package_name}: no GitHub asset configured for architecture {arch!r}"
        )

    asset_pattern = assets[arch]["name"]

    # If binaries is omitted or empty, all regular files
    # directly inside binary_dir will be linked.
    binaries = config.get("binaries")

    if binaries is None:
        binaries = []

    elif isinstance(binaries, str):
        binaries = [binaries]

    elif not isinstance(binaries, list):
        raise RuntimeError(
            f"{package_name}: 'binaries' must be a string or a list of strings"
        )

    if not all(isinstance(binary, str) and binary for binary in binaries):
        raise RuntimeError(
            f"{package_name}: 'binaries' must contain only non-empty strings"
        )

    # binary_dir is required.
    binary_dir = config.get("binary_dir")

    if not isinstance(binary_dir, str) or not binary_dir:
        raise RuntimeError(f"{package_name}: 'binary_dir' must be a non-empty string")

    # lib_dir is optional.
    lib_dir = config.get("lib_dir")

    if lib_dir is not None and (not isinstance(lib_dir, str) or not lib_dir):
        raise RuntimeError(f"{package_name}: 'lib_dir' must be a non-empty string")

    # libexec_dir is optional.
    libexec_dir = config.get("libexec_dir")

    if libexec_dir is not None and (not isinstance(libexec_dir, str) or not libexec_dir):
        raise RuntimeError(
            f"{package_name}: 'libexec_dir' must be a non-empty string"
        )

    pkg_print(
        f"Checking GitHub release: {repo}",
        color=Colors.YELLOW,
    )

    release = latest_release(repo)

    tag = release.get("tag_name")

    if not tag:
        raise RuntimeError(f"{package_name}: GitHub release has no tag_name")

    asset = find_asset(
        release,
        asset_pattern,
    )

    asset_name = asset["name"]
    download_url = asset["browser_download_url"]

    supported = (
        ".tar.gz",
        ".tgz",
        ".tar",
        ".tar.bz2",
        ".tbz2",
        ".tar.xz",
        ".txz",
        ".tar.zst",
    )

    if not asset_name.endswith(supported):
        raise RuntimeError(f"{package_name}: unsupported archive format: {asset_name}")

    package_root = LOCAL_OPT / package_name
    version_root = package_root / tag
    archive_path = version_root / asset_name

    resolved_binary_dir = binary_dir.format(version=tag)

    resolved_lib_dir = lib_dir.format(version=tag) if lib_dir is not None else None

    resolved_libexec_dir = (
        libexec_dir.format(version=tag) if libexec_dir is not None else None
    )

    LOCAL_BIN.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    version_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not archive_path.exists():
        download_file(
            download_url,
            archive_path,
        )

    archive_root = find_archive_root(
        version_root,
        resolved_binary_dir,
    )

    binary_root = archive_root / resolved_binary_dir

    needs_extraction = not binary_root.is_dir() or (
        binaries and any(not (binary_root / binary).is_file() for binary in binaries)
    )

    if needs_extraction:
        pkg_print(
            f"Extracting {asset_name}",
            color=Colors.YELLOW,
        )

        try:
            with tarfile.open(
                archive_path,
                "r:*",
            ) as archive:
                root = version_root.resolve()

                # Protect against paths such as:
                #
                # ../../somewhere/file
                #
                for member in archive.getmembers():
                    target = (version_root / member.name).resolve()

                    if target != root and root not in target.parents:
                        raise RuntimeError(
                            f"{package_name}: archive contains "
                            f"unsafe path: {member.name!r}"
                        )

                archive.extractall(
                    version_root,
                    filter="data",
                )

        except (tarfile.TarError, OSError) as exc:
            raise RuntimeError(
                f"{package_name}: failed to extract {asset_name}: {exc}"
            ) from exc

        # Recalculate because the archive may have introduced
        # a top-level directory.
        archive_root = find_archive_root(
            version_root,
            resolved_binary_dir,
        )

        binary_root = archive_root / resolved_binary_dir

    if not binary_root.is_dir():
        raise RuntimeError(f"{package_name}: binary directory not found: {binary_root}")

    # If binaries wasn't specified, discover all regular
    # files directly inside binary_root.
    #
    # Subdirectories are intentionally ignored.
    if not binaries:
        binaries = [path.name for path in binary_root.iterdir() if path.is_file()]

        if not binaries:
            raise RuntimeError(f"{package_name}: no binaries found in {binary_root}")

    # Link binaries.
    for binary in binaries:
        binary_path = binary_root / binary

        if not binary_path.is_file():
            raise RuntimeError(
                f"{package_name}: binary not found after extraction: {binary_path}"
            )

        binary_path.chmod(binary_path.stat().st_mode | 0o111)

        command_link = LOCAL_BIN / Path(binary).name

        replace_symlink(
            command_link,
            binary_path,
        )

        pkg_print(
            f"Linked {command_link} -> {binary_path}",
            color=Colors.GREEN,
        )

    # Link library directory if configured.
    #
    # Example:
    #
    #   lib/
    #   └── yosys/
    #
    # becomes:
    #
    #   ~/.local/lib/yosys
    #
    # pointing to the versioned directory.
    if resolved_lib_dir is not None:
        lib_root = archive_root / resolved_lib_dir

        if not lib_root.is_dir():
            raise RuntimeError(
                f"{package_name}: library directory not found: {lib_root}"
            )

        LOCAL_LIB.mkdir(
            parents=True,
            exist_ok=True,
        )

        for entry in lib_root.iterdir():
            destination = LOCAL_LIB / entry.name

            replace_symlink(
                destination,
                entry,
            )

            pkg_print(
                f"Linked {destination} -> {entry}",
                color=Colors.GREEN,
            )

    # Link libexec directory if configured.
    #
    # Example:
    #
    #   libexec/
    #   └── yosys-helper
    #
    # becomes:
    #
    #   ~/.local/libexec/yosys-helper
    #
    # pointing to the versioned executable.
    if resolved_libexec_dir is not None:
        libexec_root = archive_root / resolved_libexec_dir

        if not libexec_root.is_dir():
            raise RuntimeError(
                f"{package_name}: libexec directory not found: {libexec_root}"
            )

        LOCAL_LIBEXEC.mkdir(
            parents=True,
            exist_ok=True,
        )

        for entry in libexec_root.iterdir():
            destination = LOCAL_LIBEXEC / entry.name

            replace_symlink(
                destination,
                entry,
            )

            pkg_print(
                f"Linked {destination} -> {entry}",
                color=Colors.GREEN,
            )

    pkg_print(
        f"Installed {package_name} {tag}",
        color=Colors.GREEN,
        bold=True,
    )


def installed_version(
    package_name: str,
) -> str | None:
    link = LOCAL_OPT / package_name / "current"

    if not link.is_symlink():
        return None

    try:
        return link.resolve().name
    except OSError:
        return None


def release_version(repo: str) -> str:
    tag = latest_release(repo).get("tag_name")

    if not tag:
        raise RuntimeError(f"{repo}: no tag_name")

    return str(tag)
