# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH

export ZSH="$HOME/.oh-my-zsh"
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export EDITOR=nvim

# yazi change working directory
function y() {
	local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
	command yazi "$@" --cwd-file="$tmp"
	IFS= read -r -d '' cwd < "$tmp"
	[ "$cwd" != "$PWD" ] && [ -d "$cwd" ] && builtin cd -- "$cwd"
	rm -f -- "$tmp"
}

ZSH_THEME="robbyrussell"

plugins=(
  git
  zsh-autosuggestions
  fast-syntax-highlighting
  zsh-completions
  zsh-history-substring-search
  fzf-tab                     # ← game changer if you use tab a lot
  zsh-you-should-use              # optional but funny
)

source $ZSH/oh-my-zsh.sh

# Example aliases
# alias ohmyzsh="mate ~/.oh-my-zsh"
alias zshconfig="vim $HOME/.zshrc"
alias nvimconfig="cd $HOME/.config/nvim/"
alias hyprconfig="vim $HOME/.config/hypr/hyprland.conf"

alias dot="git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME"

alias nl="nmcli device wifi"

alias vim="nvim"
alias cat="bat"
alias vpn="nordvpn"

alias gs="git status"
alias gc="git commit -m"
alias gt="git tag -ma"
alias gp="git push -u --follow-tags"

# ─── Core fzf integration ────────────────────────────────────────
[ -f /usr/share/fzf/key-bindings.zsh ] && source /usr/share/fzf/key-bindings.zsh
[ -f /usr/share/fzf/completion.zsh ]   && source /usr/share/fzf/completion.zsh

export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --follow --exclude .git'

bindkey '^f' fzf-file-widget          # Ctrl+F → files (alternative to Ctrl+T)
bindkey '^r' fzf-history-widget       # history (usually already bound)
