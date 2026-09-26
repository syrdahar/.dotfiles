#!/usr/bin/env bash
# Bascule "ne pas déranger" (swaync) avec confirmation visible dans les deux sens.
if [[ $(swaync-client -D 2>/dev/null) == true ]]; then
    swaync-client -df >/dev/null
    notify-send -a dnd -u low -i notification-active-symbolic "Notifications réactivées"
else
    notify-send -a dnd -u low -i notification-disabled-symbolic "Ne pas déranger" "Les notifications sont mises en sourdine"
    sleep 1.2
    swaync-client -dn >/dev/null
fi
