#!/usr/bin/env bash
# Connecte / déconnecte NordVPN puis rafraîchit le module Waybar (signal 9).
if nordvpn status 2>/dev/null | grep -q "^Status: Connected"; then
  nordvpn disconnect >/dev/null && notify-send -a NordVPN "VPN" "Déconnecté" -i network-vpn-disconnected
else
  nordvpn connect >/dev/null && notify-send -a NordVPN "VPN" "$(nordvpn status | sed -n 's/^Country: //p') — connecté" -i network-vpn
fi
pkill -RTMIN+9 waybar
