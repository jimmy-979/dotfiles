# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.config/zsh/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export PATH="$HOME/.local/bin:$PATH"

# ohmyzsh python plugin settings
PYTHON_AUTO_VRUN=true

# source antidote
source ${ZDOTDIR:-$HOME}/.antidote/antidote.zsh

# initialize plugins statically with ${ZDOTDIR:-$HOME}/.zsh_plugins.txt
antidote load

# Set up the prompt

# autoload -Uz promptinit
# promptinit
# prompt adam1

setopt histignorealldups sharehistory

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

# Ctrl + Left / Right: move by word
bindkey '^[[1;5D' backward-word
bindkey '^[[1;5C' forward-word

# Ctrl + Delete: delete word to the right
bindkey '^[[3;5~' kill-word

# Keep 1000 lines of history within the shell and save it to ~/.zsh_history:
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=${ZDOTDIR:-$HOME}/.zsh_history

# Use modern completion system
autoload -Uz compinit
compinit

setopt complete_aliases

zstyle ':completion:*' auto-description 'specify: %d'
zstyle ':completion:*' completer _expand _complete _correct _approximate
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' menu select=2
eval "$(dircolors -b)"
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=* l:|=*'
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,tty,cputime,cmd'

# eza
alias ls='eza --icons'
alias l='eza -l --icons --group-directories-first'
alias la='eza -a --icons --group-directories-first'
alias ll='eza -lah --icons --group-directories-first'
alias tree='eza --tree --icons --group-directories-first'

# To customize prompt, run `p10k configure` or edit ~/.config/zsh/.p10k.zsh.
[[ ! -f ~/.config/zsh/.p10k.zsh ]] || source ~/.config/zsh/.p10k.zsh

# Finalize Powerlevel10k instant prompt
(( ! ${+functions[p10k]} )) || p10k finalize
