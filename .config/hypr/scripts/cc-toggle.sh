#!/usr/bin/env bash
# Boutons toggle du centre de contrôle swaync.
#   cc-toggle.sh <wifi|bluetooth|vpn|night> {set|get}
# "set" lit $SWAYNC_TOGGLE_STATE (true/false) ; "get" affiche true/false.
S=~/.config/hypr/scripts
want=${SWAYNC_TOGGLE_STATE:-false}

case "$1:$2" in
    wifi:get)      [[ $(nmcli radio wifi) == enabled ]] && echo true || echo false ;;
    wifi:set)      [[ $want == true ]] && nmcli radio wifi on || nmcli radio wifi off ;;
    bluetooth:get) bluetoothctl show 2>/dev/null | grep -q "Powered: yes" && echo true || echo false ;;
    bluetooth:set) if [[ $want == true ]]; then rfkill unblock bluetooth; sleep 0.5; bluetoothctl power on
                   else bluetoothctl power off; fi >/dev/null ;;
    vpn:get)       nordvpn status 2>/dev/null | grep -q "^Status: Connected" && echo true || echo false ;;
    vpn:set)       setsid -f ~/.config/waybar/scripts/nordvpn-toggle.sh ;;
    night:get)     [[ -f /tmp/hyprsunset_state ]] && echo true || echo false ;;
    night:set)     [[ $want == true ]] && setsid -f "$S/hyprnight.sh" on || setsid -f "$S/hyprnight.sh" off ;;
    *) echo "usage: $0 <wifi|bluetooth|vpn|night> {set|get}" >&2; exit 1 ;;
esac
