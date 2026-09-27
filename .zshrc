# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH

export ZSH="$HOME/.oh-my-zsh"
export SSH_AUTH_SOCK="$XDG_RUNTIME_DIR/ssh-agent.socket"
export EDITOR=nvim

export PATH=$PATH:~/.local/bin/

copy_dirs_content() {
    if [ "$#" -eq 0 ]; then
        echo "Usage: copy_dirs_content <dossier1> [dossier2] ..." >&2
        return 1
    fi

    local tmpfile
    tmpfile=$(mktemp)

    for dir in "$@"; do
        if [ ! -d "$dir" ]; then
            echo "Attention : '$dir' n'est pas un dossier, ignoré." >&2
            continue
        fi
		find "$dir" -type f | while IFS= read -r file; do
            echo "===== $file =====" | tee -a "$tmpfile"
            cat "$file" >> "$tmpfile"
            echo -e "\n" >> "$tmpfile"
        done
    done

    if command -v xclip >/dev/null 2>&1; then
        xclip -selection clipboard < "$tmpfile"
    elif command -v xsel >/dev/null 2>&1; then
        xsel --clipboard --input < "$tmpfile"
    elif command -v wl-copy >/dev/null 2>&1; then
        wl-copy < "$tmpfile"
    else
        echo "Aucun outil de clipboard trouvé (xclip / xsel / wl-copy)." >&2
        rm -f "$tmpfile"
        return 1
    fi

    rm -f "$tmpfile"
    echo "Contenu copié dans le presse-papier ($# dossier(s) traité(s))."
}

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
alias pdf="zathura"

alias gs="git status"
alias gc="git commit -m"
alias gt="git tag -ma"
alias gp="git push -u --follow-tags"

alias l="ls -lAh"

# ─── Core fzf integration ────────────────────────────────────────
[ -f /usr/share/fzf/key-bindings.zsh ] && source /usr/share/fzf/key-bindings.zsh
[ -f /usr/share/fzf/completion.zsh ]   && source /usr/share/fzf/completion.zsh

export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --follow --exclude .git'

bindkey -v # touches vim

bindkey '^f' fzf-file-widget          # Ctrl+F → files (alternative to Ctrl+T)
bindkey '^r' fzf-history-widget       # history (usually already bound)

export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
export PATH="$ANDROID_HOME/emulator:$PATH"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

alias claude-qwen='ANTHROPIC_BASE_URL="http://192.168.1.70:1234" ANTHROPIC_AUTH_TOKEN="sk-qwen-local-2026" ANTHROPIC_MODEL="qwen-local" claude'

# >>> Codex installer >>>
export PATH="/home/dorian/.local/bin:$PATH"
# <<< Codex installer <<<
source ~/.config/cc-providers/keys.env
alias ccq='claude --bare --settings ~/.config/cc-providers/qwen.json'

autoload -Uz add-zsh-hook
_auto_l() { [[ -o interactive ]] && l }
add-zsh-hook chpwd _auto_l

# zoxide : remplace cd (cdi = sélection interactive via fzf)
eval "$(zoxide init zsh --cmd cd)"
