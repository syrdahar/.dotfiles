#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  rice.sh — bascule du mode de barre et du look global
#
#  rice.sh bar  {islands|floating|docked|next}
#  rice.sh look {neon|glass|toggle}
#  rice.sh stats {claude|hw|toggle}  widget de droite : quotas Claude ou CPU/RAM
#  rice.sh menu        menu rofi
#  rice.sh status
#
#  Chaque variante est un fichier ; la variante active est un
#  symlink (look.conf, look.css, mode.css…). Rien d'autre à éditer.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

C=~/.config
BARS=(islands floating docked)
LOOKS=(neon glass)
STATS=(claude hw)

# Symlinks pilotés par le look : "dossier lien cible-sans-extension.ext"
LOOK_LINKS=(
    "$C/hypr      look.conf          looks/%s.conf"
    "$C/hypr      hyprlock-look.conf looks/hyprlock-%s.conf"
    "$C/waybar    look.css           looks/%s.css"
    "$C/swaync    look.css           looks/%s.css"
    "$C/rofi      look.rasi          looks/%s.rasi"
    "$C/alacritty look.toml          looks/%s.toml"
    "$C/swayosd   look.css           looks/%s.css"
    "$C/Kvantum   kvantum.kvconfig   looks/%s.kvconfig"
)

current_bar()  { basename "$(readlink "$C/waybar/mode.css")" .css; }
current_look() { basename "$(readlink "$C/hypr/look.conf")" .conf; }
current_stats() { basename "$(readlink "$C/waybar/stats.jsonc")" .jsonc; }

notify() {
    notify-send -a rice -u low -i preferences-desktop-theme \
        -h string:x-canonical-private-synchronous:rice "$@" 2>/dev/null || true
}

set_bar() {
    local mode=$1
    [[ " ${BARS[*]} " == *" $mode "* ]] || { echo "mode inconnu : $mode" >&2; exit 1; }
    ln -sfn "modes/$mode.jsonc" "$C/waybar/mode.jsonc"
    ln -sfn "modes/$mode.css"   "$C/waybar/mode.css"
    pkill -SIGUSR2 -x waybar || true
    notify "Barre · $mode"
}

set_look() {
    local look=$1 entry dir link target
    [[ " ${LOOKS[*]} " == *" $look "* ]] || { echo "look inconnu : $look" >&2; exit 1; }
    for entry in "${LOOK_LINKS[@]}"; do
        read -r dir link target <<<"$entry"
        target=$(printf "$target" "$look")
        [[ -e "$dir/$target" ]] && ln -sfn "$target" "$dir/$link"
    done
    hyprctl reload >/dev/null
    ~/.config/hypr/scripts/wm.sh reapply
    pkill -SIGUSR2 -x waybar || true
    timeout 2 swaync-client -rs >/dev/null 2>&1 || true
    notify "Look · $look"
}

set_stats() {
    local s=$1
    [[ " ${STATS[*]} " == *" $s "* ]] || { echo "stats inconnu : $s" >&2; exit 1; }
    ln -sfn "stats/$s.jsonc" "$C/waybar/stats.jsonc"
    pkill -SIGUSR2 -x waybar || true
    [[ $s == claude ]] && notify "Barre · usage Claude" || notify "Barre · CPU / RAM"
}

next_in() { # élément suivant de la liste après $1
    local cur=$1; shift; local arr=("$@") i
    for i in "${!arr[@]}"; do
        [[ ${arr[$i]} == "$cur" ]] && { echo "${arr[$(( (i + 1) % ${#arr[@]} ))]}"; return; }
    done
    echo "${arr[0]}"
}

menu() {
    local bar look choice
    bar=$(current_bar); look=$(current_look)
    choice=$(
        {
            for b in "${BARS[@]}";  do [[ $b == "$bar"  ]] && m="●" || m="○"; echo "$m  barre · $b"; done
            for l in "${LOOKS[@]}"; do [[ $l == "$look" ]] && m="●" || m="○"; echo "$m  look · $l"; done
            for s in "${STATS[@]}"; do [[ $s == "$(current_stats)" ]] && m="●" || m="○"; echo "$m  stats · $s"; done
        } | rofi -dmenu -i -p "󰏘  rice" -theme ~/.config/rofi/powermenu.rasi
    ) || exit 0
    case "$choice" in
        *"barre · "*) set_bar  "${choice##* }" ;;
        *"look · "*)  set_look "${choice##* }" ;;
        *"stats · "*) set_stats "${choice##* }" ;;
    esac
}

case "${1:-}" in
    bar)
        [[ ${2:-next} == next ]] && set_bar "$(next_in "$(current_bar)" "${BARS[@]}")" || set_bar "$2" ;;
    look)
        [[ ${2:-toggle} == toggle ]] && set_look "$(next_in "$(current_look)" "${LOOKS[@]}")" || set_look "$2" ;;
    stats)
        [[ ${2:-toggle} == toggle ]] && set_stats "$(next_in "$(current_stats)" "${STATS[@]}")" || set_stats "$2" ;;
    menu)   menu ;;
    status) echo "barre=$(current_bar) look=$(current_look) stats=$(current_stats)" ;;
    *) sed -n '3,10p' "$0" | sed 's/^#  \{0,1\}//'; exit 1 ;;
esac
