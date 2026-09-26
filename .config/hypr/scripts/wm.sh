#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  wm.sh — actions de fenêtres façon chadwm pour Hyprland
#
#  layout <master|dwindle|monocle|scrolling|prev|cycle±>
#  mfact <±0.05|reset>      taille de la zone principale (selon layout)
#  cfact <±N>               taille de la fenêtre dans sa colonne
#  zoom                     échange avec la fenêtre principale
#  nmaster <+|->            fenêtres dans la zone master
#  gaps <all|inner|outer|ih|iv|oh|ov> <±N> | gaps toggle | gaps default
#  border <±N|default>
#  hide | restore | hidden  cacher / restaurer / voir les cachées
#  allfloat                 tout le workspace flottant ↔ tuilé
#  pip                      fenêtre "picture-in-picture" (petite, épinglée)
#  gamemode                 coupe animations/blur/gaps (re-appui : rétablit)
#  reapply                  réapplique layout/gaps/bordure après un reload
#
#  État (layout, gaps, bordure) : $XDG_RUNTIME_DIR/hypr-wm.state
# ──────────────────────────────────────────────────────────────
set -uo pipefail

STATE="${XDG_RUNTIME_DIR:-/tmp}/hypr-wm.state"
LAYOUTS=(dwindle master monocle scrolling)
# Valeurs par défaut = hyprland.conf
DEF_GIN=3 DEF_GOUT=7 DEF_BORDER=2 DEF_LAYOUT=dwindle

# ── État ─────────────────────────────────────────────────────
layout=$DEF_LAYOUT prev_layout=master
gih=$DEF_GIN giv=$DEF_GIN goh=$DEF_GOUT gov=$DEF_GOUT gaps_off=0 border=$DEF_BORDER
[[ -f $STATE ]] && source "$STATE"
save() {
    cat >"$STATE" <<EOF
layout=$layout prev_layout=$prev_layout
gih=$gih giv=$giv goh=$goh gov=$gov gaps_off=$gaps_off border=$border
EOF
}

hc()  { hyprctl "$@" >/dev/null; }
kw()  { hc keyword "$@"; }
msg() { notify-send -a wm -u low -t 1200 -h string:x-canonical-private-synchronous:wm "$@" 2>/dev/null || true; }
cur_layout() { hyprctl activeworkspace -j | jq -r '.tiledLayout // "dwindle"'; }
clamp() { local v=$1; (( v < 0 )) && v=0; (( v > 60 )) && v=60; echo "$v"; }

apply_gaps() {
    if (( gaps_off )); then
        kw general:gaps_in 0; kw general:gaps_out 0
    else
        # ordre CSS : haut droite bas gauche
        kw general:gaps_in  "$giv,$gih,$giv,$gih"
        kw general:gaps_out "$gov,$goh,$gov,$goh"
    fi
}

set_layout() {
    local new=$1
    [[ $new == "$layout" ]] || prev_layout=$layout
    layout=$new
    kw general:layout "$layout"
    save
    msg "Layout · $layout"
}

case "${1:-}" in
    layout)
        case "${2:-}" in
            prev)   set_layout "$prev_layout" ;;
            cycle+|cycle-)
                    n=${#LAYOUTS[@]} i=0
                    for j in "${!LAYOUTS[@]}"; do [[ ${LAYOUTS[$j]} == "$layout" ]] && i=$j; done
                    [[ $2 == cycle+ ]] && i=$(( (i + 1) % n )) || i=$(( (i - 1 + n) % n ))
                    set_layout "${LAYOUTS[$i]}" ;;
            *)      set_layout "$2" ;;
        esac ;;

    mfact)
        case "$(cur_layout)" in
            master)    [[ $2 == reset ]] && hc dispatch layoutmsg mfact exact 0.5 || hc dispatch layoutmsg mfact "$2" ;;
            scrolling) [[ $2 == reset ]] && hc dispatch layoutmsg colresize 0.5 || hc dispatch layoutmsg colresize "$2" ;;
            dwindle)   [[ $2 == reset ]] && hc dispatch layoutmsg splitratio exact 1 \
                                        || hc dispatch layoutmsg splitratio "$(awk -v d="$2" 'BEGIN{printf "%+.2f", d*2}')" ;;
        esac ;;

    cfact)  # chadwm : +25 % → fenêtre plus haute dans sa pile
        [[ $2 == reset ]] && { hc dispatch layoutmsg splitratio exact 1; exit; }
        hc dispatch resizeactive 0 "$2" ;;

    zoom)
        if [[ $(cur_layout) == master ]]; then
            hc dispatch layoutmsg swapwithmaster auto
        else
            # dwindle & co : échange avec la fenêtre tuilée la plus en haut à gauche
            ws=$(hyprctl activeworkspace -j | jq .id)
            me=$(hyprctl activewindow -j | jq -r .address)
            first=$(hyprctl clients -j | jq -r --argjson ws "$ws" \
                '[.[] | select(.workspace.id == $ws and .floating == false)] | sort_by(.at[0], .at[1]) | .[0].address')
            [[ -n $first && $first != null && $first != "$me" ]] && hc dispatch swapwindow "address:$first"
        fi ;;

    nmaster)
        [[ $(cur_layout) == master ]] || { msg "nmaster : layout master uniquement (SUPER+T)"; exit; }
        [[ $2 == + ]] && hc dispatch layoutmsg addmaster || hc dispatch layoutmsg removemaster ;;

    gaps)
        case "${2:-}" in
            toggle)  gaps_off=$(( !gaps_off )) ;;
            default) gih=$DEF_GIN giv=$DEF_GIN goh=$DEF_GOUT gov=$DEF_GOUT gaps_off=0 ;;
            all)     gih=$(clamp $((gih + $3))) giv=$(clamp $((giv + $3))) goh=$(clamp $((goh + $3))) gov=$(clamp $((gov + $3))) ;;
            inner)   gih=$(clamp $((gih + $3))) giv=$(clamp $((giv + $3))) ;;
            outer)   goh=$(clamp $((goh + $3))) gov=$(clamp $((gov + $3))) ;;
            ih)      gih=$(clamp $((gih + $3))) ;;
            iv)      giv=$(clamp $((giv + $3))) ;;
            oh)      goh=$(clamp $((goh + $3))) ;;
            ov)      gov=$(clamp $((gov + $3))) ;;
        esac
        apply_gaps; save ;;

    border)
        [[ $2 == default ]] && border=$DEF_BORDER || border=$(( border + $2 ))
        (( border < 0 )) && border=0; (( border > 10 )) && border=10
        kw general:border_size "$border"; save ;;

    hide)
        hc dispatch movetoworkspacesilent special:hidden
        msg "Fenêtre cachée" "SUPER+SHIFT+E pour la restaurer" ;;
    restore)
        ws=$(hyprctl activeworkspace -j | jq .id)
        addr=$(hyprctl clients -j | jq -r \
            '[.[] | select(.workspace.name == "special:hidden")] | sort_by(.focusHistoryID) | .[0].address // empty')
        [[ -n $addr ]] && hc dispatch movetoworkspace "$ws,address:$addr" || msg "Aucune fenêtre cachée" ;;
    hidden)
        hc dispatch togglespecialworkspace hidden ;;

    allfloat)
        ws=$(hyprctl activeworkspace -j | jq .id)
        mapfile -t tiled < <(hyprctl clients -j | jq -r --argjson ws "$ws" '.[] | select(.workspace.id == $ws and .floating == false) | .address')
        if (( ${#tiled[@]} )); then
            for a in "${tiled[@]}"; do hc dispatch setfloating "address:$a"; done
            msg "Workspace flottant"
        else
            for a in $(hyprctl clients -j | jq -r --argjson ws "$ws" '.[] | select(.workspace.id == $ws) | .address'); do
                hc dispatch settiled "address:$a"
            done
            msg "Workspace tuilé"
        fi ;;

    pip)
        if [[ $(hyprctl activewindow -j | jq .pinned) == true ]]; then
            hc --batch "dispatch pin; dispatch settiled"
        else
            hc --batch "dispatch setfloating; dispatch resizeactive exact 32% 32%; dispatch moveactive exact 66% 62%; dispatch pin"
        fi ;;

    gamemode)
        if [[ $(hyprctl getoption animations:enabled -j | jq .int) == 1 ]]; then
            hc --batch "keyword animations:enabled 0; keyword decoration:blur:enabled 0; keyword decoration:shadow:enabled 0; \
                        keyword general:gaps_in 0; keyword general:gaps_out 0; keyword decoration:rounding 0; keyword general:border_size 1"
            msg "Mode jeu activé" "animations, blur, ombres et gaps coupés"
        else
            hc reload; sleep 0.3; "$0" reapply
            msg "Mode jeu désactivé"
        fi ;;

    reapply)
        kw general:layout "$layout"; apply_gaps; kw general:border_size "$border" ;;

    *) sed -n '3,19p' "$0" | sed 's/^#  \{0,1\}//'; exit 1 ;;
esac
