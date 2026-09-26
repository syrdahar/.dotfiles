#!/bin/bash

# CONFIGURATION
TEMP_LOW=3000 # Night temperature
TEMP_MID=4000   # Evening/Morning temperature
TEMP_HIGH=4400 # Day (default)
LAT="48.9"      # Optional: for future sun-tracking expansion
LON="2.3"

STATE_FILE="/tmp/hyprsunset_state"

# Function to apply temperature
apply_temp() {
    pkill hyprsunset
    if [ "$1" == "default" ]; then
        hyprsunset --default
        rm -f "$STATE_FILE"
    else
        hyprsunset --temperature "$1"
        echo "$1" > "$STATE_FILE"
    fi
}

case "$1" in
    on)
        apply_temp $TEMP_LOW
        ;;
    off)
        apply_temp "default"
        ;;
    toggle)
        # notify avant apply_temp : hyprsunset reste au premier plan
        if [ -f "$STATE_FILE" ]; then
            notify-send -a "Lumière nocturne" -u low -i weather-clear-symbolic \
                -h string:x-canonical-private-synchronous:night "Lumière nocturne désactivée"
            apply_temp "default"
        else
            notify-send -a "Lumière nocturne" -u low -i weather-clear-night-symbolic \
                -h string:x-canonical-private-synchronous:night "Lumière nocturne activée" "${TEMP_LOW}K"
            apply_temp $TEMP_LOW
        fi
        ;;
    auto)
        HOUR=$(date +%H)
        if [ "$HOUR" -ge 21 ] || [ "$HOUR" -lt 06 ]; then
            apply_temp $TEMP_LOW
        elif [ "$HOUR" -ge 18 ] || [ "$HOUR" -ge 06 -a "$HOUR" -lt 09 ]; then
            apply_temp $TEMP_MID
        else
            apply_temp "default"
        fi
        ;;
    *)
        echo "Usage: $0 {on|off|toggle|auto}"
        exit 1
        ;;
esac
