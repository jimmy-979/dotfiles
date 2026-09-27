# `packages.toml` Documentation

This document describes the structure and available options for the
`packages.toml` manifest used by `pkg`.

The manifest describes:

-   Logical packages managed by `pkg`
-   The provider used on each Linux distribution
-   Package names for system package managers
-   GitHub AppImage releases
-   Architecture-specific GitHub assets
-   Configuration files and where they should be linked
-   Groups containing multiple system packages

------------------------------------------------------------------------

## 1. Basic Structure

All package definitions live under:

``` toml
[packages.<package-name>]
```

For example:

``` toml
[packages.zsh]
command = "zsh"
```

The name (`zsh` in this example) is the logical name used by `pkg`:

``` bash
pkg install zsh
```

If no package names are given to `pkg install`, all packages in the
manifest are processed:

``` bash
pkg install
```

------------------------------------------------------------------------

# 2. `command`

The optional `command` field specifies the executable that represents
the package.

``` toml
[packages.zsh]
command = "zsh"
```

This is particularly useful for `pkg check`, because `pkg` can use the
command to determine whether the package is installed.

For example:

``` toml
[packages.neovim]
command = "nvim"
```

The logical package name is `neovim`, while the executable is `nvim`.

If `command` is omitted, `pkg` uses the logical package name as the
command when checking the package.

------------------------------------------------------------------------

# 3. Distribution-specific Configuration

Each package can have a section for the supported distribution:

``` toml
[packages.zsh.debian]
```

or:

``` toml
[packages.zsh.arch]
```

Currently supported distributions are:

| Distribution      | Manifest section   |
| ----------------- | ------------------ |
| Debian / Ubuntu   | `debian`           |
| Arch Linux        | `arch`             |

`pkg` detects the current distribution automatically.

For example, on Debian:

``` toml
[packages.zsh.debian]
provider = "apt"
name = "zsh"
```

On Arch:

``` toml
[packages.zsh.arch]
provider = "pacman"
name = "zsh"
```

------------------------------------------------------------------------

# 4. `provider`

The `provider` field specifies how the package is installed.

Currently available providers are:

-   `apt`
-   `pacman`
-   `aur`
-   `github`

Example:

``` toml
[packages.zsh.debian]
provider = "apt"
name = "zsh"
```

------------------------------------------------------------------------

# 5. `name`

For `apt`, `pacman`, and `aur`, the `name` field specifies the package
name.

## Single package

``` toml
[packages.zsh.debian]
provider = "apt"
name = "zsh"
```

## Multiple packages

`name` can also be a list:

``` toml
[packages.common.debian]
provider = "apt"
name = [
    "eza",
    "build-essential",
]
```

On Arch, the equivalent can use Arch-specific package names:

``` toml
[packages.common.arch]
provider = "pacman"
name = [
    "eza",
    "base-devel",
]
```

This allows one logical package to represent a group of system packages.

For example:

``` bash
pkg install common
```

can install multiple packages in one operation.

------------------------------------------------------------------------

# 6. APT

Use the `apt` provider for Debian/Ubuntu packages.

``` toml
[packages.zsh.debian]
provider = "apt"
name = "zsh"
```

Multiple packages:

``` toml
[packages.common.debian]
provider = "apt"
name = [
    "eza",
    "build-essential",
    "cmake",
    "ninja-build",
]
```

`pkg` installs these using `apt-get`.

------------------------------------------------------------------------

# 7. Pacman

Use the `pacman` provider for packages available in the Arch
repositories.

``` toml
[packages.zsh.arch]
provider = "pacman"
name = "zsh"
```

Multiple packages:

``` toml
[packages.common.arch]
provider = "pacman"
name = [
    "eza",
    "base-devel",
    "cmake",
    "ninja",
]
```

`pkg` installs these using `pacman -S`.

------------------------------------------------------------------------

# 8. AUR

Use the `aur` provider for packages from the Arch User Repository.

``` toml
[packages.some-tool.arch]
provider = "aur"
name = "some-tool"
```

Multiple AUR packages can also be specified:

``` toml
[packages.aur-tools.arch]
provider = "aur"
name = [
    "package-one",
    "package-two",
]
```

The current implementation uses `yay` for the AUR provider.

`yay` must already be installed for this provider to work.

------------------------------------------------------------------------

# 9. GitHub Releases

The `github` provider is intended for applications distributed through
GitHub releases.

Currently the supported GitHub package type is:

``` toml
type = "appimage"
```

Example:

``` toml
[packages.neovim.debian]
provider = "github"
repo = "neovim/neovim"
type = "appimage"
```

The repository is specified as:

``` toml
repo = "owner/repository"
```

For example:

``` toml
repo = "neovim/neovim"
```

`pkg` queries the latest GitHub release and downloads the appropriate
release asset.

------------------------------------------------------------------------

# 10. GitHub Assets and Architectures

GitHub AppImage packages can define different assets for different CPU
architectures.

Example:

``` toml
[packages.neovim.debian.assets.arm64]
name = "nvim-linux-arm64.appimage"

[packages.neovim.debian.assets.x86_64]
name = "nvim-linux-x86_64.appimage"
```

The supported architecture names currently used by `pkg` are:

| Machine architecture   | Manifest architecture   |
| ---------------------- | ----------------------- |
| `x86_64` / `amd64`     | `x86_64`                |
| `aarch64` / `arm64`    | `arm64`                 |
| `armv7l` / `armv7`     | `armv7`                 |

`pkg` detects the current architecture and selects the corresponding
asset.

For example, on an ARM64 machine:

``` text
arm64
    ↓
assets.arm64
    ↓
nvim-linux-arm64.appimage
```

------------------------------------------------------------------------

# 11. Complete GitHub Example

A complete Neovim definition can look like:

``` toml
[packages.neovim]
command = "nvim"

[packages.neovim.debian]
provider = "github"
repo = "neovim/neovim"
type = "appimage"

[packages.neovim.debian.assets.arm64]
name = "nvim-linux-arm64.appimage"

[packages.neovim.debian.assets.x86_64]
name = "nvim-linux-x86_64.appimage"

[packages.neovim.arch]
provider = "aur"
name = "neovim"
```

On Debian/Ubuntu, `pkg` uses the GitHub AppImage.

On Arch, `pkg` uses the AUR package.

------------------------------------------------------------------------

# 12. Configuration Files

A package can also define configuration files.

The basic form is:

``` toml
[packages.neovim.config]
source = "config/nvim"
destination = "~/.config/nvim"
```

`source` is relative to the root of the `pkg` repository.

For example:

``` text
.
├── packages.toml
├── pkg.py
└── config/
    └── nvim/
        ├── init.lua
        └── lua/
```

The destination supports `~` and environment-variable expansion.

For example:

``` toml
destination = "~/.config/nvim"
```

------------------------------------------------------------------------

# 13. Configuration `mode`

There are currently two configuration modes:

-   `link`
-   `contents`

If `mode` is omitted, it defaults to `link`.

## 13.1 `link`

`link` links the source itself to the destination.

``` toml
[packages.neovim.config]
source = "config/nvim"
destination = "~/.config/nvim"
mode = "link"
```

This results in:

``` text
~/.config/nvim -> <repository>/config/nvim
```

Because `link` is the default, this can also be written as:

``` toml
[packages.neovim.config]
source = "config/nvim"
destination = "~/.config/nvim"
```

------------------------------------------------------------------------

# 14. `contents`

`contents` is useful when a configuration directory contains files that
need to be placed directly into another directory.

For example, Zsh configuration files normally live directly in `$HOME`:

``` text
config/
└── zsh/
    ├── .zshrc
    ├── .zprofile
    └── .zshenv
```

Use:

``` toml
[packages.zsh.config]
source = "config/zsh"
destination = "~"
mode = "contents"
```

The result is:

``` text
~/.zshrc    -> <repository>/config/zsh/.zshrc
~/.zprofile -> <repository>/config/zsh/.zprofile
~/.zshenv   -> <repository>/config/zsh/.zshenv
```

This keeps the configuration files organized inside the repository
without requiring the repository itself to live in `$HOME`.

------------------------------------------------------------------------

# 15. Multiple Configuration Entries

A package can have multiple independent configuration entries.

Use TOML's array-of-tables syntax:

``` toml
[[packages.zsh.config]]
source = "config/zsh/.zshrc"
destination = "~/.zshrc"

[[packages.zsh.config]]
source = "config/zsh/.zprofile"
destination = "~/.zprofile"

[[packages.zsh.config]]
source = "config/zsh/.zshenv"
destination = "~/.zshenv"
```

This is useful when configuration files belong in different directories.

For example:

``` toml
[[packages.git.config]]
source = "config/git/.gitconfig"
destination = "~/.gitconfig"

[[packages.git.config]]
source = "config/git/ignore"
destination = "~/.config/git/ignore"
```

A package can therefore manage configuration across multiple locations.

------------------------------------------------------------------------

# 16. Mixing Configuration Modes

Each configuration entry has its own mode.

For example:

``` toml
[[packages.example.config]]
source = "config/example/main"
destination = "~/.config/example"
mode = "link"

[[packages.example.config]]
source = "config/example/home"
destination = "~"
mode = "contents"
```

The first entry links the directory itself.

The second entry links everything inside `config/example/home` into
`$HOME`.

------------------------------------------------------------------------

# 17. Configuration Safety

`pkg` does not silently overwrite an existing real file or directory.

If the destination already contains a real file or directory,
configuration installation fails rather than destroying the existing
data.

Existing symlinks can be replaced when necessary.

For example, if:

``` text
~/.zshrc
```

is already a symlink to the repository's `.zshrc`, `pkg` recognizes that
it is already correctly configured.

------------------------------------------------------------------------

# 18. Example: Neovim

A typical Neovim definition:

``` toml
[packages.neovim]
command = "nvim"

[packages.neovim.debian]
provider = "github"
repo = "neovim/neovim"
type = "appimage"

[packages.neovim.debian.assets.arm64]
name = "nvim-linux-arm64.appimage"

[packages.neovim.debian.assets.x86_64]
name = "nvim-linux-x86_64.appimage"

[packages.neovim.arch]
provider = "aur"
name = "neovim"

[packages.neovim.config]
source = "config/nvim"
destination = "~/.config/nvim"
```

Install:

``` bash
pkg install neovim
```

------------------------------------------------------------------------

# 19. Example: Zsh

``` toml
[packages.zsh]
command = "zsh"

[packages.zsh.debian]
provider = "apt"
name = "zsh"

[packages.zsh.arch]
provider = "pacman"
name = "zsh"

[packages.zsh.config]
source = "config/zsh"
destination = "~"
mode = "contents"
```

Repository:

``` text
config/
└── zsh/
    ├── .zshrc
    ├── .zprofile
    └── .zshenv
```

Install:

``` bash
pkg install zsh
```

------------------------------------------------------------------------

# 20. Example: Common Development Tools

A useful way to represent packages that don't correspond to one
particular application is to create a logical group:

``` toml
[packages.common]
```

Then define the packages per distribution:

``` toml
[packages.common.debian]
provider = "apt"
name = [
    "eza",
    "build-essential",
    "cmake",
    "ninja-build",
    "gdb",
]

[packages.common.arch]
provider = "pacman"
name = [
    "eza",
    "base-devel",
    "cmake",
    "ninja",
    "gdb",
]
```

Now:

``` bash
pkg install common
```

installs the appropriate group for the current distribution.

This is particularly useful when the equivalent package has a different
name on different distributions.

For example:

``` text
Debian        Arch
--------      ---------
build-essential
              base-devel
```

------------------------------------------------------------------------

# 21. Example Complete Manifest

Putting everything together:

``` toml
# ---------------------------------------------------------------------------
# Neovim
# ---------------------------------------------------------------------------

[packages.neovim]
command = "nvim"

[packages.neovim.debian]
provider = "github"
repo = "neovim/neovim"
type = "appimage"

[packages.neovim.debian.assets.arm64]
name = "nvim-linux-arm64.appimage"

[packages.neovim.debian.assets.x86_64]
name = "nvim-linux-x86_64.appimage"

[packages.neovim.arch]
provider = "aur"
name = "neovim"

[packages.neovim.config]
source = "config/nvim"
destination = "~/.config/nvim"


# ---------------------------------------------------------------------------
# Zsh
# ---------------------------------------------------------------------------

[packages.zsh]
command = "zsh"

[packages.zsh.debian]
provider = "apt"
name = "zsh"

[packages.zsh.arch]
provider = "pacman"
name = "zsh"

[packages.zsh.config]
source = "config/zsh"
destination = "~"
mode = "contents"


# ---------------------------------------------------------------------------
# Common development tools
# ---------------------------------------------------------------------------

[packages.common]

[packages.common.debian]
provider = "apt"
name = [
    "eza",
    "build-essential",
    "cmake",
    "ninja-build",
    "gdb",
]

[packages.common.arch]
provider = "pacman"
name = [
    "eza",
    "base-devel",
    "cmake",
    "ninja",
    "gdb",
]
```

------------------------------------------------------------------------

# 22. Quick Reference

## Package

``` toml
[packages.<name>]
command = "<executable>"
```

`command` is optional.

## Debian / Ubuntu

``` toml
[packages.<name>.debian]
provider = "apt"
name = "<package>"
```

or:

``` toml
name = ["<package1>", "<package2>"]
```

## Arch repository

``` toml
[packages.<name>.arch]
provider = "pacman"
name = "<package>"
```

or:

``` toml
name = ["<package1>", "<package2>"]
```

## Arch AUR

``` toml
[packages.<name>.arch]
provider = "aur"
name = "<package>"
```

or:

``` toml
name = ["<package1>", "<package2>"]
```

## GitHub AppImage

``` toml
[packages.<name>.debian]
provider = "github"
repo = "<owner>/<repository>"
type = "appimage"

[packages.<name>.debian.assets.<architecture>]
name = "<asset-name>"
```

## Configuration

``` toml
[packages.<name>.config]
source = "<repository-path>"
destination = "<destination-path>"
mode = "link"
```

or:

``` toml
[packages.<name>.config]
source = "<repository-path>"
destination = "<destination-path>"
mode = "contents"
```

## Multiple configurations

``` toml
[[packages.<name>.config]]
source = "<repository-path>"
destination = "<destination-path>"

[[packages.<name>.config]]
source = "<another-repository-path>"
destination = "<another-destination-path>"
```

------------------------------------------------------------------------

# 23. Commands

Install everything:

``` bash
pkg install
```

Install selected logical packages:

``` bash
pkg install neovim
```

Install several logical packages:

``` bash
pkg install neovim zsh common
```

Check installed packages:

``` bash
pkg check
```

Show the `pkg` version:

``` bash
pkg --version
```
