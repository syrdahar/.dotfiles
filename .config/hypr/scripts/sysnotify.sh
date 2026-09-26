#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Notifications système (lancé en exec-once) :
#   - batterie : faible 20 %, critique 10 %, veille auto à 4 %
#   - chargeur branché / débranché, charge terminée
#   - Wi-Fi / Ethernet connecté ou perdu
# ──────────────────────────────────────────────────────────────

BAT=/sys/class/power_supply/BAT0
AC=/sys/class/power_supply/AC
LOW=20
CRITICAL=10
SUSPEND=4

# Une seule instance
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/sysnotify.lock"
flock -n 9 || exit 0

notify() { notify-send -a "Système" "$@"; }

# ── Réseau (événements NetworkManager) ───────────────────────
watch_network() {
    nmcli monitor 2>/dev/null | while read -r line; do
        dev=${line%%:*}
        [[ $dev =~ ^(wl|en|eth) ]] || continue      # ignore nordlynx, docker, lo…
        case "$line" in
            *": connected")
                ssid=$(nmcli -t -f GENERAL.CONNECTION dev show "$dev" 2>/dev/null | cut -d: -f2-)
                if [[ $dev == wl* ]]; then
                    notify -u low -i network-wireless-signal-excellent-symbolic "Wi-Fi connecté" "$ssid"
                else
                    notify -u low -i network-wired-symbolic "Ethernet connecté" "$ssid"
                fi ;;
            *": disconnected"|*": unavailable")
                notify -u normal -i network-offline-symbolic "Connexion perdue" "$dev" ;;
        esac
    done
}
watch_network &
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# ── Batterie / secteur ───────────────────────────────────────
last_ac=$(<"$AC/online")
last_status=$(<"$BAT/status")
warned_low=0
warned_crit=0

while sleep 5; do
    cap=$(<"$BAT/capacity")
    status=$(<"$BAT/status")
    ac=$(<"$AC/online")

    if [[ $ac != "$last_ac" ]]; then
        if [[ $ac == 1 ]]; then
            notify -u low -i ac-adapter-symbolic -h string:x-canonical-private-synchronous:power \
                "Chargeur branché" "Batterie à $cap %"
        else
            notify -u low -i battery-symbolic -h string:x-canonical-private-synchronous:power \
                "Sur batterie" "$cap % restants"
        fi
        last_ac=$ac
    fi

    if [[ $status == Full && $last_status != Full ]]; then
        notify -u low -i battery-full-charged-symbolic "Batterie chargée" "Tu peux débrancher le chargeur"
    fi
    last_status=$status

    if [[ $ac == 1 ]]; then
        warned_low=0; warned_crit=0
        continue
    fi

    if (( cap <= SUSPEND )); then
        notify -u critical -i battery-empty-symbolic "Batterie vide ($cap %)" "Mise en veille dans 60 s…"
        sleep 60
        [[ $(<"$AC/online") == 0 ]] && systemctl suspend
    elif (( cap <= CRITICAL && ! warned_crit )); then
        notify -u critical -i battery-caution-symbolic "Batterie critique · $cap %" "Branche le chargeur maintenant"
        warned_crit=1; warned_low=1
    elif (( cap <= LOW && ! warned_low )); then
        notify -u normal -i battery-low-symbolic "Batterie faible · $cap %" "Pense à brancher le chargeur"
        warned_low=1
    fi
done
