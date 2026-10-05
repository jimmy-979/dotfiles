## How to install misc tools for RISCV development

### Mise

```bash
curl https://mise.jdx.dev/install.sh | sh
```

### RISC-V Toolchain

```bash
sudo npm install --location=global xpm@latest
xpm install @xpack-dev-tools/riscv-none-elf-gcc@latest --global --verbose
```

### Sail RISC-V


```bash
curl --location https://github.com/riscv/sail-riscv/releases/download/0.14.1/sail-riscv-$(uname)-$(arch).tar.gz | sudo tar xvz --directory=/path/to/install --strip-components=1
```