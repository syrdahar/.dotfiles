#!/usr/bin/env bash
# Pipette : copie la couleur dans le presse-papier et affiche une notif avec un aperçu.
color=$(hyprpicker -a -f hex) || exit 0
[[ -z $color ]] && exit 0
preview="${XDG_RUNTIME_DIR:-/tmp}/colorpicker.png"
magick -size 64x64 "xc:$color" "$preview"
notify-send -a "Pipette" -u low -i "$preview" "$color" "Copiée dans le presse-papier"
