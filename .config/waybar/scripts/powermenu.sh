#!/usr/bin/env bash
# Power menu rofi (thème ~/.config/rofi/powermenu.rasi)

lock="󰌾  Verrouiller"
suspend="󰤄  Veille"
logout="󰍃  Déconnexion"
reboot="󰜉  Redémarrer"
shutdown="⏻  Éteindre"

chosen=$(printf '%s\n' "$lock" "$suspend" "$logout" "$reboot" "$shutdown" |
  rofi -dmenu -i -p "$(uptime -p | sed 's/^up /  /')" -theme ~/.config/rofi/powermenu.rasi)

case "$chosen" in
  "$lock")     pidof hyprlock || hyprlock ;;
  "$suspend")  systemctl suspend ;;
  "$logout")   hyprctl dispatch exit ;;
  "$reboot")   systemctl reboot ;;
  "$shutdown") systemctl poweroff ;;
esac
