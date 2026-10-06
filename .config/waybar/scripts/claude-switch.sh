#!/usr/bin/env bash
# Bascule vers le compte Claude avec le plus de marge, notifie, rafraîchit le widget.
out=$(cswap switch --strategy best 2>&1)
notify-send -a "Claude Code" -u low -i system-switch-user-symbolic "Changement de compte" "$(tail -n 3 <<<"$out")"
pkill -RTMIN+10 waybar
