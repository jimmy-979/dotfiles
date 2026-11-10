import json
import re
import shutil
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from packages import LOCAL_BIN, LOCAL_OPT, Colors, pkg_print


def github_release(
    repo: str,
    release: str | None = None,
) -> dict[str, Any]:
    """
    Get a GitHub release.

    If release is omitted or set to "latest", the latest release
    is returned.

    Otherwise, release is treated as a GitHub release tag.
    """

    if release is None or release == "latest":
        url = f"https://api.github.com/repos/{repo}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{repo}/releases/tags/{release}"

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


def download_file(
    url: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dotfiles-pkg"},
    )

    progress_stream = None

    try:
        with (
            urllib.request.urlopen(request) as response,
            destination.open("wb") as f,
        ):
            if sys.stdout.isatty():
                progress_stream = sys.stdout
            elif sys.stderr.isatty():
                progress_stream = sys.stderr

            try:
                total_size = int(response.headers.get("Content-Length", ""))
            except ValueError:
                total_size = 0

            downloaded = 0
            started_at = time.monotonic()
            last_reported = started_at

            while chunk := response.read(64 * 1024):
                f.write(chunk)
                downloaded += len(chunk)

                now = time.monotonic()
                if now - last_reported < 0.2 and downloaded != total_size:
                    continue

                elapsed = max(now - started_at, 0.001)
                speed = downloaded / elapsed
                progress = f"{downloaded / total_size:.1%}" if total_size else ""
                size = (
                    f"{_format_bytes(downloaded)} / {_format_bytes(total_size)}"
                    if total_size
                    else f"{_format_bytes(downloaded)}"
                )
                # Keep the progress display on one terminal row. Printing the
                # full URL can make the line wrap; carriage returns cannot
                # overwrite text that has wrapped onto another terminal row.
                details = f"{progress} {size} at {_format_bytes(speed)}/s".strip()
                label = f"pkg: Downloading {destination.name}"
                terminal_width = shutil.get_terminal_size(fallback=(100, 20)).columns
                available_label_width = max(0, terminal_width - len(details) - 3)

                if len(label) > available_label_width:
                    if available_label_width >= 3:
                        label = label[: available_label_width - 3] + "..."
                    else:
                        label = label[:available_label_width]

                status = f"{label} [{details}]" if label else f"[{details}]"
                line = Colors.wrap(status, Colors.YELLOW)

                if progress_stream is not None:
                    progress_stream.write(f"\r{line}\033[K")
                    progress_stream.flush()

                last_reported = now

            if total_size and downloaded != total_size:
                raise OSError(
                    f"incomplete download: expected {total_size} bytes, "
                    f"received {downloaded}"
                )

            if progress_stream is not None:
                progress_stream.write("\n")
                progress_stream.flush()
            else:
                elapsed = max(time.monotonic() - started_at, 0.001)
                progress = f"{downloaded / total_size:.1%}" if total_size else ""
                size = (
                    f"{_format_bytes(downloaded)} / {_format_bytes(total_size)}"
                    if total_size
                    else f"{_format_bytes(downloaded)}"
                )
                pkg_print(
                    f"Downloaded {url} [{progress} {size} at "
                    f"{_format_bytes(downloaded / elapsed)}/s]",
                    color=Colors.YELLOW,
                )

    except Exception as exc:
        if progress_stream is not None:
            progress_stream.write("\n")
            progress_stream.flush()
        if destination.exists():
            destination.unlink()

        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def _format_bytes(size: float) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


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


def get_release(
    package_name: str,
    repo: str,
    config: dict,
) -> dict[str, Any]:
    """
    Get the configured GitHub release.

    If 'release' is omitted, the latest release is used.
    """

    release = config.get("release")

    if release is not None and (not isinstance(release, str) or not release):
        raise RuntimeError(f"{package_name}: 'release' must be a non-empty string")

    if release is None or release == "latest":
        release_description = "latest"
    else:
        release_description = release

    pkg_print(
        f"Checking GitHub release: {repo} ({release_description})",
        color=Colors.YELLOW,
    )

    return github_release(
        repo,
        release,
    )


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

    release = get_release(
        package_name,
        repo,
        config,
    )

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


def link_directory(
    package_name: str,
    source_root: Path,
    destination_root: Path,
    description: str,
) -> None:
    """
    Link all direct children of source_root into destination_root.

    Existing real files/directories are never replaced.
    Existing symlinks are replaced.
    """

    if not source_root.is_dir():
        raise RuntimeError(
            f"{package_name}: {description} directory not found: {source_root}"
        )

    destination_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    for entry in source_root.iterdir():
        destination = destination_root / entry.name

        replace_symlink(
            destination,
            entry,
        )

        pkg_print(
            f"Linked {destination} -> {entry}",
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

    # If binaries is omitted or empty, all regular files directly inside
    # the selected binary directory will be linked when binary_dir is not
    # configured.
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

    # binary_dir is optional.
    #
    # When specified, the archive is treated as a self-contained package
    # directory and nothing is linked into ~/.local/bin.
    binary_dir = config.get("binary_dir")

    if binary_dir is not None and (not isinstance(binary_dir, str) or not binary_dir):
        raise RuntimeError(f"{package_name}: 'binary_dir' must be a non-empty string")

    release = get_release(
        package_name,
        repo,
        config,
    )

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
        ".zip",
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

    resolved_binary_dir = (
        binary_dir.format(version=tag) if binary_dir is not None else None
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

    if resolved_binary_dir is not None:
        # binary_dir explicitly identifies a directory inside the archive.
        archive_root = find_archive_root(
            version_root,
            resolved_binary_dir,
        )
        binary_root = archive_root / resolved_binary_dir
    else:
        # Without binary_dir, binaries are expected at the archive root or
        # inside its single top-level directory.
        directories = [entry for entry in version_root.iterdir() if entry.is_dir()]

        archive_root = directories[0] if len(directories) == 1 else version_root
        binary_root = archive_root

    needs_extraction = not binary_root.is_dir()

    if (resolved_binary_dir is None and binaries) or (
        resolved_binary_dir is not None and binaries
    ):
        needs_extraction = needs_extraction or any(
            not (binary_root / binary).is_file() for binary in binaries
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

                # Protect against paths such as ../../somewhere/file.
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

        # Recalculate after extraction because the archive may have introduced
        # a top-level directory.
        if resolved_binary_dir is not None:
            archive_root = find_archive_root(
                version_root,
                resolved_binary_dir,
            )
            binary_root = archive_root / resolved_binary_dir
        else:
            directories = [entry for entry in version_root.iterdir() if entry.is_dir()]
            archive_root = directories[0] if len(directories) == 1 else version_root
            binary_root = archive_root

    if not binary_root.is_dir():
        raise RuntimeError(f"{package_name}: binary directory not found: {binary_root}")

    # Maintain a stable path to the extracted package directory. For an
    # archive such as package-version/bin, this points to package-version.
    current_link = package_root / "current"

    replace_symlink(
        current_link,
        archive_root,
    )

    pkg_print(
        f"Linked {current_link} -> {archive_root}",
        color=Colors.GREEN,
    )

    # If binary_dir is configured, the archive is a self-contained package.
    # Do not expose its binaries individually through ~/.local/bin.
    if binary_dir is not None:
        pkg_print(
            f"Installed {package_name} {tag}",
            color=Colors.GREEN,
            bold=True,
        )
        return

    # If binaries wasn't specified, discover all regular files directly
    # inside binary_root. Subdirectories are intentionally ignored.
    if not binaries:
        binaries = [path.name for path in binary_root.iterdir() if path.is_file()]

        if not binaries:
            raise RuntimeError(f"{package_name}: no binaries found in {binary_root}")

    LOCAL_BIN.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    tag = github_release(repo).get("tag_name")

    if not tag:
        raise RuntimeError(f"{repo}: no tag_name")

    return str(tag)
