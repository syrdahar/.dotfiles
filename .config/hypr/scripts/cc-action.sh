#!/usr/bin/env bash
# Boutons "one-shot" du centre de contrôle swaync : ferme le panneau puis agit.
S=~/.config/hypr/scripts
swaync-client -cp >/dev/null 2>&1
case "$1" in
    screenshot) sleep 0.4; hyprshot -m region ;;
    picker)     sleep 0.3; "$S/colorpicker.sh" ;;
    lock)       sleep 0.3; pidof hyprlock || hyprlock ;;
    power)      ~/.config/waybar/scripts/powermenu.sh ;;
    look)       "$S/rice.sh" look toggle ;;
    bar)        "$S/rice.sh" bar next ;;
esac
