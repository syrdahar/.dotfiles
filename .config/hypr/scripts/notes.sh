#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Notes à la volée dans ~/notes/scratchpad
#   notes.sh toggle   fenêtre flottante nvim (scratchpad Hyprland :
#                     reste ouverte en arrière-plan, apparaît/disparaît)
#   notes.sh quick    ajoute une ligne via rofi, sans ouvrir l'éditeur
# ──────────────────────────────────────────────────────────────
FILE=~/notes/scratchpad
CLASS=notes-scratch
mkdir -p "$(dirname "$FILE")"; touch "$FILE"

case "${1:-toggle}" in
    toggle)
        if ! hyprctl clients -j | jq -e --arg c "$CLASS" 'any(.[]; .class == $c)' >/dev/null; then
            # Sauvegarde auto à chaque modif / perte de focus ; curseur en fin de fichier
            hyprctl dispatch exec "alacritty --class $CLASS -T 'notes · scratchpad' \
                -e nvim + -c 'set autoread wrap linebreak' \
                -c 'autocmd TextChanged,InsertLeave,FocusLost,BufLeave * silent! update' \
                -c 'autocmd FocusGained * checktime' $FILE" >/dev/null
            sleep 0.4
        fi
        hyprctl dispatch togglespecialworkspace notes >/dev/null ;;
    quick)
        line=$(rofi -dmenu -p "󰏫  note" -l 0 -theme-str 'window { width: 560px; }' </dev/null) || exit 0
        [[ -z $line ]] && exit 0
        # garantit un retour à la ligne avant d'ajouter
        [[ -s $FILE && $(tail -c1 "$FILE" | wc -l) -eq 0 ]] && echo >>"$FILE"
        printf '%s\n' "$line" >>"$FILE"
        notify-send -a Notes -u low -i document-edit-symbolic "Note ajoutée" "$line" ;;
esac
