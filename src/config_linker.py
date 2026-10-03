from pathlib import Path

from config import config_source_path, expand_path
from packages import Colors, pkg_print


def configure_package(package_name: str, package: dict) -> None:
    config = package.get("config")
    if config is None:
        return
    if isinstance(config, dict):
        configs = [config]
    elif isinstance(config, list):
        configs = config
    else:
        raise TypeError(f"{package_name}: config must be a table or array of tables")

    pkg_print(f"Configuring {package_name}", color=Colors.MAGENTA, bold=True)
    for entry in configs:
        if not isinstance(entry, dict):
            raise TypeError(f"{package_name}: each config entry must be a table")
        source = entry.get("source")
        destination = entry.get("destination")
        mode = entry.get("mode", "link")
        if not source or not destination:
            raise RuntimeError(
                f"{package_name}: config requires 'source' and 'destination'"
            )
        if mode not in {"link", "contents"}:
            raise RuntimeError(
                f"{package_name}: unsupported config mode {mode!r}; expected 'link' or 'contents'"
            )
        source_path = config_source_path(source)
        destination_path = expand_path(destination)
        if not source_path.exists():
            raise RuntimeError(
                f"{package_name}: configuration source does not exist: {source_path}"
            )
        if mode == "contents" and not source_path.is_dir():
            raise RuntimeError(
                f"{package_name}: config source must be a directory when mode='contents': {source_path}"
            )
        if mode == "link":
            _link_config_path(package_name, source_path, destination_path)
        else:
            destination_path.mkdir(parents=True, exist_ok=True)
            for item in sorted(source_path.iterdir()):
                _link_config_path(package_name, item, destination_path / item.name)


def _link_config_path(
    package_name: str, source_path: Path, destination_path: Path
) -> None:
    source_resolved = source_path.resolve()
    if destination_path.is_symlink():
        try:
            if destination_path.resolve() == source_resolved:
                pkg_print(
                    f"Config already linked: {destination_path} -> {source_path}",
                    color=Colors.GREEN,
                )
                return
        except OSError:
            pass
        pkg_print(
            f"Replacing existing symlink: {destination_path}", color=Colors.YELLOW
        )
        destination_path.unlink()
    elif destination_path.exists():
        raise RuntimeError(
            f"{package_name}: refusing to replace existing file or directory: {destination_path}"
        )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.symlink_to(source_resolved)
    pkg_print(f"Linked {destination_path} -> {source_path}", color=Colors.GREEN)
