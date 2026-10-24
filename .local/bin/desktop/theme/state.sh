# shellcheck shell=bash
# ──────────────────────────────────────────────────────────────
#  theme/state.sh — état partagé de desk theme et desk wall (sourcé, pas exécuté)
#
#  state_get CLÉ [défaut]    lit une valeur de ~/.local/state/desk/theme/state
#  state_set CLÉ VALEUR      écrit une valeur (réécriture atomique)
#  Clés : palette (auto | <preset>, défaut auto) · wallpaper (chemin absolu)
#         rotate (on | off, défaut on)
# ──────────────────────────────────────────────────────────────
THEME_DIR=~/.local/bin/desktop/theme
PAL_DIR=~/.config/desktop/theme/palettes
WALL_DIR=${DESK_WALL_DIR:-$HOME/Images/Wallpapers}
WALL_DIR=${WALL_DIR/#\~/$HOME}          # « ~/… » dans desk.conf (sans guillemets)
WALL_CUR=~/.cache/desk/wall/current
THEME_STATE_DIR=${XDG_STATE_HOME:-$HOME/.local/state}/desk/theme
THEME_STATE=$THEME_STATE_DIR/state
PAL_JSON=$THEME_STATE_DIR/palette.json

state_get() {
    local key=$1 def=${2:-} line
    line=$(grep -m1 "^${key}=" "$THEME_STATE" 2>/dev/null || true)
    if [[ -n $line ]]; then printf '%s' "${line#*=}"; else printf '%s' "$def"; fi
}

state_set() {
    local key=$1 val=$2 tmp
    mkdir -p "$THEME_STATE_DIR"
    tmp=$(mktemp "$THEME_STATE.XXXXXX")
    { grep -v "^${key}=" "$THEME_STATE" 2>/dev/null || true; printf '%s=%s\n' "$key" "$val"; } >"$tmp"
    mv -f "$tmp" "$THEME_STATE"
}
