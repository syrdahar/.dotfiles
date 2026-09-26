#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  OSD volume / micro / luminosité.
#  Via swayosd (pilule en bas au centre, ~/.config/swayosd/) ;
#  repli sur une notification swaync si swayosd-server ne tourne pas.
#  Usage : osd.sh {vol-up|vol-down|vol-mute|mic-mute|bri-up|bri-down}
# ──────────────────────────────────────────────────────────────

if pgrep -x swayosd-server >/dev/null; then
    case "$1" in
        vol-up)   exec swayosd-client --output-volume raise --max-volume 150 ;;
        vol-down) exec swayosd-client --output-volume lower ;;
        vol-mute) exec swayosd-client --output-volume mute-toggle ;;
        mic-mute) exec swayosd-client --input-volume mute-toggle ;;
        bri-up)   exec swayosd-client --brightness raise ;;
        bri-down) exec swayosd-client --brightness lower ;;
    esac
fi

SINK=@DEFAULT_AUDIO_SINK@
SOURCE=@DEFAULT_AUDIO_SOURCE@
osd() { notify-send -a osd -u low -t 1400 -h string:x-canonical-private-synchronous:osd -h int:value:"$2" -i "$3" "$1"; }
volume() {
    local out vol; out=$(wpctl get-volume "$SINK"); vol=$(awk '{printf "%d", $2 * 100}' <<<"$out")
    if [[ $out == *MUTED* ]]; then osd "Son coupé" 0 audio-volume-muted-symbolic
    else osd "Volume · $vol%" "$vol" audio-volume-high-symbolic; fi
}
case "$1" in
    vol-up)   wpctl set-mute "$SINK" 0; wpctl set-volume -l 1.5 "$SINK" 5%+; volume ;;
    vol-down) wpctl set-volume "$SINK" 5%-; volume ;;
    vol-mute) wpctl set-mute "$SINK" toggle; volume ;;
    mic-mute) wpctl set-mute "$SOURCE" toggle
              [[ $(wpctl get-volume "$SOURCE") == *MUTED* ]] && osd "Micro coupé" 0 microphone-sensitivity-muted-symbolic \
                                                              || osd "Micro actif" 100 audio-input-microphone-symbolic ;;
    bri-up|bri-down)
              [[ $1 == bri-up ]] && step=5%+ || step=5%-
              brightnessctl -q -e4 -n2 set "$step"
              pct=$(brightnessctl -m | cut -d, -f4 | tr -d %); osd "Luminosité · $pct%" "$pct" display-brightness-symbolic ;;
    *) echo "Usage: $0 {vol-up|vol-down|vol-mute|mic-mute|bri-up|bri-down}" >&2; exit 1 ;;
esac
