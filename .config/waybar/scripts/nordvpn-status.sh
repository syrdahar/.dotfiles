#!/usr/bin/env bash
# Statut NordVPN pour Waybar (JSON). Appelé par custom/vpn.
command -v nordvpn >/dev/null || exit 0

out=$(timeout 3 nordvpn status 2>/dev/null)
status=$(sed -n 's/^Status: //p' <<<"$out")

if [[ "$status" == "Connected" ]]; then
  country=$(sed -n 's/^Country: //p' <<<"$out")
  city=$(sed -n 's/^City: //p' <<<"$out")
  server=$(sed -n 's/^Hostname: //p' <<<"$out")
  printf '{"text":"󰒃","tooltip":"VPN : %s, %s\\n%s","class":"connected"}\n' "$country" "$city" "$server"
else
  printf '{"text":"󰦞","tooltip":"VPN déconnecté (clic pour connecter)","class":"disconnected"}\n'
fi
