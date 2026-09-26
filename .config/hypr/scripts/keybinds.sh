#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Aide des raccourcis (rofi) générée depuis `hyprctl binds`.
#  Chaque bind est déclaré avec `bindd` (description) dans
#  hyprland.conf : cette liste est donc toujours à jour.
#  Recherche par action ("fermer") ou par touches ("shift q").
#  Entrée : exécute le raccourci sélectionné.
# ──────────────────────────────────────────────────────────────

binds=$(hyprctl binds -j | jq -c '[.[] | select(.has_description)]')

list=$(jq -r '
  def mods:
    [ (if (.modmask / 64 | floor) % 2 == 1 then "SUPER" else empty end),
      (if (.modmask / 4  | floor) % 2 == 1 then "CTRL"  else empty end),
      (if (.modmask / 8  | floor) % 2 == 1 then "ALT"   else empty end),
      (if  .modmask             % 2 == 1 then "SHIFT" else empty end) ];
  def keyname:
    { "ampersand":"& (1)", "eacute":"é (2)", "quotedbl":"\" (3)", "apostrophe":"'"'"' (4)",
      "parenleft":"( (5)", "minus":"- (6)", "egrave":"è (7)", "underscore":"_ (8)",
      "ccedilla":"ç (9)", "agrave":"à (0)", "twosuperior":"²", "exclam":"!",
      "comma":",", "semicolon":";", "Return":"Entrée", "Escape":"Échap", "escape":"Échap", "space":"Espace",
      "Tab":"Tab", "left":"←", "right":"→", "up":"↑", "down":"↓", "Print":"Impr",
      "mouse:272":"clic gauche", "mouse:273":"clic droit", "mouse:274":"clic molette",
      "mouse_down":"molette ↓", "mouse_up":"molette ↑",
      "XF86AudioRaiseVolume":"Volume +", "XF86AudioLowerVolume":"Volume −",
      "XF86AudioMute":"Muet", "XF86AudioMicMute":"Micro muet",
      "XF86MonBrightnessUp":"Luminosité +", "XF86MonBrightnessDown":"Luminosité −",
      "XF86AudioNext":"Piste suivante", "XF86AudioPrev":"Piste précédente",
      "XF86AudioPlay":"Lecture", "XF86AudioPause":"Pause",
      "XF86SelectiveScreenshot":"Touche capture" } as $k
    | ($k[.key] // (.key | if length == 1 then ascii_upcase else . end));
  .[] | ((mods + [keyname]) | join(" + ")) as $combo
      | (if .submap != "" then "[" + .submap + "] " else "" end) as $sm
      | "\($sm)\($combo)\t\(.description)"
' <<<"$binds" | awk -F'\t' '{ printf "%-34s  %s\n", $1, $2 }')

[[ ${1:-} == --print ]] && { echo "$list"; exit 0; }

idx=$(rofi -dmenu -i -format i -matching normal -p "󰌌  raccourcis" \
        -mesg "Tape une action ou des touches · Entrée exécute" \
        -theme ~/.config/rofi/keybinds.rasi <<<"$list") || exit 0
[[ -z $idx ]] && exit 0

read -r dispatcher arg < <(jq -r --argjson i "$idx" '.[$i] | "\(.dispatcher) \(.arg)"' <<<"$binds")
case $dispatcher in
    movewindow|resizewindow) exit 0 ;;   # binds souris : rien à exécuter
    *) hyprctl dispatch "$dispatcher" "$arg" >/dev/null ;;
esac
