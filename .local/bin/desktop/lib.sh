# shellcheck shell=bash
# ──────────────────────────────────────────────────────────────
#  lib.sh — fonctions communes aux scripts desk-* (sourcé, pas exécuté)
#
#  t "français" "english"          texte dans la langue courante (DESK_LANG : fr | en)
#  bi "fr ‖ en" / bi_row "fr ‖ en"  libellé bilingue → langue courante / « courant ‖ autre »
#  menu "prompt" [options rofi…]   entrées sur stdin → ligne choisie (code ≠ 0 si annulé)
#                                  une ligne « visible ‖ mots-clés » : la partie après ‖ est
#                                  cachée mais cherchable (recherche FR + EN quelle que soit la langue)
#  notify [options] titre [corps]  notification (app "desk")
#  die "message"                   notification d'erreur + sortie
#  clip_get / clip_set [texte]     presse-papier Wayland (clip_set lit stdin sans argument)
#  active_cwd                      dossier courant du terminal actif (sinon $HOME ; DESK_CWD le force)
#  is_git_repo [dossier]
#  $DESK_JQ                        fonctions jq pour afficher un bind (combo, fullcombo)
# ──────────────────────────────────────────────────────────────
set -Eeuo pipefail
shopt -s inherit_errexit

DESK_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
DESK_THEME=~/.config/rofi/desk.rasi
DESK_RUN=${XDG_RUNTIME_DIR:-/tmp}/desk
DESK_NAME=${DESK_NAME:-$(basename "$0")}
DESK_CONF=~/.config/desktop
DESK_STATE=${XDG_STATE_HOME:-$HOME/.local/state}/desk
mkdir -p "$DESK_RUN" "$DESK_STATE"; rm -f "$DESK_RUN/died.$$"
export PATH="$DESK_DIR:$PATH"

# Réglages utilisateur (navigateur, moteur de recherche…) : ~/.config/desktop/desk.conf
DESK_BROWSER=xdg-open
DESK_TERMINAL=alacritty
DESK_LANG=en
# shellcheck source=/dev/null
[[ -f $DESK_CONF/desk.conf ]] && source "$DESK_CONF/desk.conf"

# ── Langue d'affichage : fr | en (bascule : desk lang toggle · SUPER+Espace puis l) ──
# La recherche dans rofi marche toujours dans les deux langues.
[[ -f $DESK_STATE/lang ]] && DESK_LANG=$(<"$DESK_STATE/lang")
[[ $DESK_LANG == fr ]] || DESK_LANG=en
export DESK_LANG

t() { if [[ $DESK_LANG == fr ]]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }

# Libellés bilingues « français ‖ english »
bi() {
    local s=$1
    [[ $s == *" ‖ "* ]] || { printf '%s' "$s"; return; }
    if [[ $DESK_LANG == fr ]]; then printf '%s' "${s%% ‖ *}"; else printf '%s' "${s#* ‖ }"; fi
}
bi_other() {
    local s=$1
    [[ $s == *" ‖ "* ]] || return 0
    if [[ $DESK_LANG == fr ]]; then printf '%s' "${s#* ‖ }"; else printf '%s' "${s%% ‖ *}"; fi
}
bi_row() { local o; o=$(bi_other "$1"); printf '%s%s\n' "$(bi "$1")" "${o:+ ‖ $o}"; }

# Mode test (CLI) : DESK_TEST=1 → notifications sur stderr ;
# DESK_CLIP_IN="…" remplace le presse-papier lu, DESK_CLIP_OUT=fichier reçoit ce qui serait copié.
notify() {
    if [[ -n ${DESK_TEST:-} ]]; then local a; for a; do [[ $a == -* ]] || printf '[notif] %s\n' "$a" >&2; done; return 0; fi
    notify-send -a desk "$@" 2>/dev/null || true
}

die() {
    notify -u critical -i dialog-error-symbolic "$DESK_NAME" "$*"
    echo "$DESK_NAME: $*" >&2
    touch "$DESK_RUN/died.$$"       # $$ = script parent, même depuis un $(…) : évite la 2e notif (trap ERR)
    exit 1
}

# Toute erreur non gérée remonte aussi en notification
desk_on_err() {
    local rc=$1 line=$2 cmd=$3
    if [[ -e $DESK_RUN/died.$$ ]]; then rm -f "$DESK_RUN/died.$$"; exit "$rc"; fi
    notify -u critical -i dialog-error-symbolic "$DESK_NAME : $(t erreur error)" "$(t ligne line) $line : $cmd (code $rc)"
}
trap 'desk_on_err $? $LINENO "$BASH_COMMAND"' ERR

menu() {
    local prompt=$1; shift
    # « visible ‖ mots-clés » → mots-clés en champ meta rofi (invisibles, cherchables)
    perl -pe 's/ ‖ (.*)$/\0meta\x1f$1/' | rofi -dmenu -i -p "$prompt" -theme "$DESK_THEME" "$@"
}

clip_get() {
    if [[ -n ${DESK_CLIP_IN+x} ]]; then printf '%s' "$DESK_CLIP_IN"; return; fi
    wl-paste --no-newline 2>/dev/null || true
}

clip_set() {
    local out=${DESK_CLIP_OUT:-}
    if [[ -n $out ]]; then
        if (( $# )); then printf '%s' "$1" >"$out"; else cat >"$out"; fi
        return
    fi
    # sorties redirigées : wl-copy reste en arrière-plan et ne doit pas garder le pipe de l'appelant
    if (( $# )); then printf '%s' "$1" | wl-copy >/dev/null 2>&1; else wl-copy >/dev/null 2>&1; fi
}

is_git_repo() { git -C "${1:-.}" rev-parse --is-inside-work-tree &>/dev/null; }

# ── Secrets ──────────────────────────────────────────────────
# Motifs PCRE (grep -P) : clés privées, JWT, clés d'API connues,
# "password=…"-like, en-têtes Authorization, URLs avec mot de passe.
DESK_SECRET_RE='-----BEGIN [A-Z ]*PRIVATE KEY-----'
DESK_SECRET_RE+='|\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'
DESK_SECRET_RE+='|\bsk-(ant-|proj-)?[A-Za-z0-9_-]{20,}'
DESK_SECRET_RE+='|\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}|\bglpat-[A-Za-z0-9_-]{20,}'
DESK_SECRET_RE+='|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_-]{35}|\bxox[abprs]-[A-Za-z0-9-]{10,}'
DESK_SECRET_RE+='|\b[rs]k_live_[A-Za-z0-9]{16,}|\bnpm_[A-Za-z0-9]{36}|\bhf_[A-Za-z0-9]{30,}'
# clé=valeur : valeur entre guillemets (≥ 4 car.) ou brute contenant au moins un
# chiffre/symbole (exclut le code : token = getToken(), key: process.env.KEY…)
DESK_SECRET_RE+='|(?i:(?<![a-z])(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)\w*["'"'"']?\s*[:=]\s*'
DESK_SECRET_RE+='("[^"\s][^"]{3,}"|'"'"'[^'"'"'\s][^'"'"']{3,}'"'"'|(?![A-Za-z_.]+(?=[\s,;()]|$))[A-Za-z0-9_\-+/=.~!@#$%^&*]{6,}(?=[\s,;]|$)))'
DESK_SECRET_RE+='|(?i:\bauthorization:\s*(bearer|basic|token)\s+\S+)'
DESK_SECRET_RE+='|\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@'

# is_sensitive < texte   → code 0 si un secret est détecté
is_sensitive() { grep -qP -- "$DESK_SECRET_RE"; }

# mask_secrets < texte   → texte avec les secrets remplacés par «[MASQUÉ]» / «[REDACTED]»
mask_secrets() {
    perl -pe 'BEGIN { $re = shift @ARGV; $m = shift @ARGV } s/$re/$m/g' -- "$DESK_SECRET_RE" "$(t '[MASQUÉ]' '[REDACTED]')" 2>/dev/null
}

# show_text "titre" fichier [langage]   affiche un fichier dans un terminal flottant (bat)
show_text() {
    local title=$1 file=$2 lang=${3:-txt}
    hyprctl dispatch exec "alacritty --class desk-float -T '$title' -e bat --paging=always --style=plain -l '$lang' '$file'" >/dev/null
}

# float_run "titre" dossier commande…   lance une commande dans un terminal flottant
#   (la fenêtre attend une touche à la fin, pour lire le résultat)
float_run() {
    local title=$1 dir=$2; shift 2
    DESK_DONE=$(t terminé done) DESK_ANYKEY=$(t "une touche pour fermer" "press any key to close") setsid -f "$DESK_TERMINAL" --class desk-float -T "$title" --working-directory "$dir" -e bash -c \
        '"$@"; rc=$?; printf "\n\e[2m── %s (code %s) · %s ──\e[0m" "$DESK_DONE" "$rc" "$DESK_ANYKEY"; read -rsn1' _ "$@" >/dev/null 2>&1
}

# float_pager "titre" dossier "commande shell"   sortie (couleurs) paginée dans less, terminal flottant
float_pager() {
    setsid -f "$DESK_TERMINAL" --class desk-float -T "$1" --working-directory "$2" -e bash -c \
        "($3) 2>&1 | less -R" >/dev/null 2>&1
}

# term_run "titre" dossier commande…   terminal normal (tuilé) qui exécute la commande
term_run() {
    local title=$1 dir=$2; shift 2
    setsid -f "$DESK_TERMINAL" -T "$title" --working-directory "$dir" -e "$@" >/dev/null 2>&1
}

open_url() {
    if [[ $DESK_BROWSER == xdg-open ]]; then setsid -f xdg-open "$1" >/dev/null 2>&1
    else hyprctl dispatch exec "$DESK_BROWSER '$1'" >/dev/null; fi
}

urlencode() { python3 -c 'import sys,urllib.parse as u; print(u.quote_plus(sys.argv[1]), end="")' "$1"; }

# confirm "question ?"   → code 0 si « Oui / Yes »
confirm() {
    local idx
    idx=$(printf '%s\n%s\n' "$(t Non No) ‖ $(t No Non)" "$(t Oui Yes) ‖ $(t Yes Oui)" | menu "$1" -format i) || return 1
    [[ $idx == 1 ]]
}

# run_bind "description exacte d'un bindd"   exécute ce bind (même action que le raccourci)
run_bind() {
    local d a
    read -r d a < <(hyprctl binds -j | jq -r --arg x "$1" 'first(.[] | select(.description == $x)) | "\(.dispatcher) \(.arg)"')
    [[ -n ${d:-} && $d != null ]] || die "$(t "Bind introuvable" "Bind not found") : $1"
    hyprctl dispatch "$d" "$a" >/dev/null
}

tilde() { local p=$1; [[ $p == "$HOME"* ]] && p="~${p#"$HOME"}"; printf '%s' "$p"; }

# Registre d'actions partagé par les modules, exposé à la palette via --list :
#   ACTIONS=("id|Libellé FR ‖ English label" …) ; fonctions a_<id> (tirets → _)
list_actions() { local e id label; for e in "${ACTIONS[@]}"; do IFS='|' read -r id label <<<"$e"; printf '%s\t%s\n' "$id" "$label"; done; }
run_action()   {
    local fn="a_${1//-/_}"; shift
    declare -F "$fn" >/dev/null || die "$(t "Action inconnue" "Unknown action") : ${fn#a_}"
    "$fn" "$@"
}
menu_actions() {   # menu_actions "prompt" "message"  → choisit dans ACTIONS puis l'exécute
    local -a ids=() labels=(); local e id label idx
    for e in "${ACTIONS[@]}"; do IFS='|' read -r id label <<<"$e"; ids+=("$id"); labels+=("$label"); done
    idx=$(for label in "${labels[@]}"; do bi_row "$label"; done | menu "$1" -format i -mesg "$2") || exit 0
    [[ -n $idx ]] || exit 0
    run_action "${ids[$idx]}"
}

# Dossier courant du terminal actif, sans daemon :
# fenêtre active → pid du terminal → shell enfant → processus au premier plan du tty
# (tpgid) ; si c'est un client tmux, on demande le dossier du pane actif à tmux.
active_cwd() {
    # DESK_CWD=dossier : forcer le dossier (CLI, tests)
    [[ -n ${DESK_CWD:-} ]] && { echo "$DESK_CWD"; return; }
    local pid shell fg leaf cwd="" tty
    pid=$(hyprctl activewindow -j 2>/dev/null | jq -r '.pid // 0')
    if (( pid > 0 )) && [[ -d /proc/$pid ]]; then
        shell=$(cat /proc/"$pid"/task/*/children 2>/dev/null | tr ' ' '\n' | grep . | sort -n | tail -1 || true)
        leaf=${shell:-$pid}
        if [[ -n $shell ]]; then
            # champ 8 de /proc/<pid>/stat (après le nom entre parenthèses) = groupe au premier plan
            fg=$(sed 's/.*) //' /proc/"$shell"/stat 2>/dev/null | awk '{print $6}' || true)
            [[ -n $fg && $fg -gt 0 && -d /proc/$fg ]] && leaf=$fg
        fi
        if [[ $(cat /proc/"$leaf"/comm 2>/dev/null) == tmux* ]]; then
            tty=$(readlink /proc/"$leaf"/fd/0 2>/dev/null || true)
            [[ -n $tty ]] && cwd=$(tmux display-message -p -c "$tty" '#{pane_current_path}' 2>/dev/null || true)
        fi
        [[ -n $cwd ]] || cwd=$(readlink /proc/"$leaf"/cwd 2>/dev/null || true)
    fi
    [[ -n $cwd && -d $cwd ]] && echo "$cwd" || echo "$HOME"
}

# Affichage d'un bind de `hyprctl binds -j` (mêmes noms de touches que scripts/keybinds.sh)
# shellcheck disable=SC2016
DESK_JQ='
def mods:
  [ (if (.modmask / 64 | floor) % 2 == 1 then "SUPER" else empty end),
    (if (.modmask / 4  | floor) % 2 == 1 then "CTRL"  else empty end),
    (if (.modmask / 8  | floor) % 2 == 1 then "ALT"   else empty end),
    (if  .modmask             % 2 == 1 then "SHIFT" else empty end) ];
def keyname:
  (if $ENV.DESK_LANG == "fr" then {} else
   { "Return":"Enter", "Escape":"Esc", "escape":"Esc", "space":"Space", "Print":"Print",
     "mouse:272":"left click", "mouse:273":"right click", "mouse:274":"middle click",
     "mouse_down":"wheel↓", "mouse_up":"wheel↑", "catchall":"any key",
     "XF86AudioMute":"Mute", "XF86AudioMicMute":"MicMute", "XF86MonBrightnessUp":"Brightness+",
     "XF86MonBrightnessDown":"Brightness−", "XF86AudioNext":"NextTrack", "XF86AudioPrev":"PrevTrack",
     "XF86AudioPlay":"Play", "XF86SelectiveScreenshot":"ScreenshotKey" } end) as $en
  | { "ampersand":"&(1)", "eacute":"é(2)", "quotedbl":"\"(3)", "apostrophe":"'"'"'(4)",
    "parenleft":"((5)", "minus":"-(6)", "egrave":"è(7)", "underscore":"_(8)",
    "ccedilla":"ç(9)", "agrave":"à(0)", "twosuperior":"²", "exclam":"!",
    "comma":",", "semicolon":";", "colon":":", "Return":"Entrée", "Escape":"Échap", "escape":"Échap",
    "space":"Espace", "Tab":"Tab", "left":"←", "right":"→", "up":"↑", "down":"↓", "Print":"Impr",
    "mouse:272":"clic gauche", "mouse:273":"clic droit", "mouse:274":"clic molette",
    "mouse_down":"molette↓", "mouse_up":"molette↑", "catchall":"autre touche",
    "XF86AudioRaiseVolume":"Volume+", "XF86AudioLowerVolume":"Volume−",
    "XF86AudioMute":"Muet", "XF86AudioMicMute":"MicroMuet",
    "XF86MonBrightnessUp":"Luminosité+", "XF86MonBrightnessDown":"Luminosité−",
    "XF86AudioNext":"PisteSuivante", "XF86AudioPrev":"PistePrécédente",
    "XF86AudioPlay":"Lecture", "XF86AudioPause":"Pause",
    "XF86SelectiveScreenshot":"ToucheCapture" } as $k
  | ($en[.key] // $k[.key] // (.key | if length == 1 then ascii_upcase else . end));
def combo: (mods + [keyname]) | join("+");
# touche qui ouvre un submap : bind "submap, <nom>" ou, pour le leader, "desk leader enter"
def entry($all; $sm):
  ([ $all[] | select(.submap == "" and (
        (.dispatcher == "submap" and .arg == $sm) or
        ($sm == "leader" and .dispatcher == "exec" and (.arg | test("desk leader enter$"))))) ]
   | first) as $e
  | if $e then ($e | combo) else "[" + $sm + "]" end;
# libellé bilingue « fr ‖ en » → langue courante / autre langue ("" si monolingue)
def bi:       if test(" ‖ ") then (split(" ‖ ") | if $ENV.DESK_LANG == "fr" then .[0] else .[1] end) else . end;
def bi_other: if test(" ‖ ") then (split(" ‖ ") | if $ENV.DESK_LANG == "fr" then .[1] else .[0] end) else "" end;
def fullcombo($all): if .submap == "" then combo else entry($all; .submap) + " → " + combo end;
# commande normalisée pour comparer une action de palette à un bind exec
def norm: sub("^pkill rofi \\|\\| "; "") | sub("^\\S*/desk "; "desk ") | sub("^desk leader "; "desk ");
'
