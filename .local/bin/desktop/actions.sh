# shellcheck shell=bash
# ──────────────────────────────────────────────────────────────
#  Actions de la palette (SUPER+X, ou SUPER+Espace puis Espace).
#  Une ligne = une action, dans l'ordre d'affichage :
#
#   action "Catégorie · Libellé ‖ Category · Label" cmd  "commande shell"  ["description d'un bind"]
#   action "Catégorie · Libellé ‖ Category · Label" bind "description exacte d'un bindd"
#
#  Libellé bilingue « français ‖ english » : affiché dans la langue courante
#  (desk lang toggle), l'autre langue reste cherchable.
#  Le raccourci affiché à droite est retrouvé tout seul dans `hyprctl binds` :
#   - bind : le(s) bind(s) qui portent cette description (on exécute ce bind) ;
#   - cmd  : le(s) bind(s) exec qui lancent la même commande
#            ("desk x" ≡ "~/.local/bin/desktop/desk x" ≡ "desk leader x"),
#            ou ceux qui portent la description donnée en 4e argument.
#  Dans une commande, `desk` est dans le PATH.
# ──────────────────────────────────────────────────────────────

# ── Command center ───────────────────────────────────────────
action "Aide · Cheatsheet de tous les raccourcis ‖ Help · Cheatsheet of all shortcuts"          cmd  "desk cheatsheet"
action "Aide · Liste des raccourcis (keybinds.sh) ‖ Help · Shortcut list (keybinds.sh)"         bind "Aide · Afficher tous les raccourcis"
action "Langue · Basculer français / anglais ‖ Language · Toggle French / English"              cmd  "desk lang toggle"
action "Scratchpad · Terminal (tmux) ‖ Scratchpad · Terminal (tmux)"                            cmd  "desk scratch term"
action "Scratchpad · btop ‖ Scratchpad · btop (system monitor)"                                 cmd  "desk scratch btop"
action "Scratchpad · Notes (nvim) ‖ Scratchpad · Notes (nvim)"                                  bind "Notes · Ouvrir/cacher le scratchpad"
action "Scratchpad · Magic (afficher/cacher) ‖ Scratchpad · Magic (toggle)"                     bind "Workspace · Scratchpad afficher/cacher"
action "Scratchpad · Envoyer la fenêtre dans Magic ‖ Scratchpad · Send window to Magic"         bind "Workspace · Envoyer au scratchpad"

# ── Presse-papier (desk clip) ────────────────────────────────
action "Presse-papier · Actions selon le contenu copié ‖ Clipboard · Actions for copied content" cmd  "desk clip"
action "Presse-papier · Historique ‖ Clipboard · History"                                        bind "Apps · Historique du presse-papier"
action "Calcul · Calculatrice et conversions (qalc) ‖ Calc · Calculator and unit conversions (qalc)" cmd "desk calc"
# toutes les actions de desk-clip (URL, JSON, JWT, texte, générateurs…), lues dans le script
while IFS=$'\t' read -r id label; do
    [[ $id == calc || $id == history ]] && continue          # déjà listées au-dessus
    case $label in
        Générer*) action "$label" cmd "desk clip run $id" ;;
        Outils*)  fr=${label%% ‖ *}; en=${label#* ‖ }
                  action "Presse-papier · ${fr#Outils · } ‖ Clipboard · ${en#Tools · }" cmd "desk clip run $id" ;;
        *)        action "Presse-papier · ${label/ ‖ / ‖ Clipboard · }" cmd "desk clip run $id" ;;
    esac
done < <("$DESK_DIR/desk-clip" --list)

# ── Dev (phase 3) ────────────────────────────────────────────
action "Projet · Ouvrir / rejoindre un projet ‖ Project · Open / switch to a project"  cmd  "desk project"
action "Git · Menu git du dossier courant ‖ Git · Git menu for current directory"      cmd  "desk git"
action "Docker · Conteneurs ‖ Docker · Containers"                                     cmd  "desk docker"
action "Ports · Ports en écoute et processus ‖ Ports · Listening ports and processes"  cmd  "desk ports"
action "Processus · Par CPU / RAM (tuer, inspecter…) ‖ Processes · By CPU / RAM (kill, inspect…)" cmd "desk procs"
action "SSH · Se connecter à un hôte ‖ SSH · Connect to a host"                        cmd  "desk ssh"
action "Web · Recherche (gh mdn npm aur so…) ‖ Web · Search (gh mdn npm aur so…)"      cmd  "desk web"
action "Mobile · scrcpy / émulateur / adb ‖ Mobile · scrcpy / emulator / adb"          cmd  "desk mobile"
action "IA · Claude sur le presse-papier (expliquer, corriger, tests…) ‖ AI · Claude on clipboard (explain, fix, tests…)" cmd "desk ai"
action "IA · ChatGPT : question rapide (calcul, conversion, info, ?web) ‖ AI · ChatGPT: quick question (math, conversion, facts, ?web)" cmd "desk gpt"
action "Système · Audio, Wi-Fi, Bluetooth, VPN, session ‖ System · Audio, Wi-Fi, Bluetooth, VPN, session" cmd "desk system"
action "Notes · Notes et TODO (~/notes) ‖ Notes · Notes and TODOs (~/notes)"              cmd "desk notes"
action "Focus · Minuteur, pomodoro, mode focus ‖ Focus · Timer, pomodoro, focus mode"      cmd "desk focus"
action "Capture · Menu captures (OCR, annotation, vidéo…) ‖ Screenshot · Capture menu (OCR, annotate, video…)" cmd "desk capture"
action "Drive · Proton Drive (parcourir, envoyer, lien) ‖ Drive · Proton Drive (browse, upload, link)" cmd "desk drive"
# sous-actions de chaque module, lues dans les scripts (desk-<module> --list)
for mod in project git docker ports procs mobile capture ai system notes focus claudenotify drive; do
    while IFS=$'\t' read -r id label; do
        case "$mod:$id" in
            project:pick|docker:containers|ports:ports|procs:cpu) continue ;;       # = menus ci-dessus
            capture:region-clip|capture:screen-clip|capture:region-file|capture:window-file|capture:screen-file|capture:picker)
                continue ;;                                                         # = tes binds, listés plus bas
            system:mic|system:dnd|system:night|system:lock|system:power|system:reload|notes:scratch|notes:quick)
                continue ;;                                                         # idem
        esac
        action "$label" cmd "desk $mod run $id"
    done < <("$DESK_DIR/desk-$mod" --list)
done

# ── Existant : notes, captures ───────────────────────────────
action "Notes · Ajouter une ligne rapide ‖ Notes · Quick note (one line)"              bind "Notes · Ajouter une ligne rapide"
action "Capture · Zone → fichier ‖ Screenshot · Region → file"                         bind "Capture · Zone (fichier)"
action "Capture · Fenêtre → fichier ‖ Screenshot · Window → file"                      bind "Capture · Fenêtre (fichier)"
action "Capture · Écran entier → fichier ‖ Screenshot · Full screen → file"            bind "Capture · Écran entier (fichier)"
action "Capture · Zone → presse-papier ‖ Screenshot · Region → clipboard"              bind "Capture · Zone → presse-papier (chadwm)"
action "Capture · Écran → presse-papier ‖ Screenshot · Screen → clipboard"             bind "Capture · Écran → presse-papier (chadwm)"
action "Couleur · Pipette (hexa copié) ‖ Color · Color picker (hex copied)"            bind "Apps · Pipette de couleur"

# ── Existant : applications ──────────────────────────────────
action "Apps · Terminal ‖ Apps · Terminal"                                             bind "Apps · Terminal"
action "Apps · Lanceur d'applications ‖ Apps · Application launcher"                   bind "Apps · Lanceur d'applications"
action "Apps · Navigateur ‖ Apps · Web browser"                                        bind "Apps · Navigateur"
action "Apps · Gestionnaire de fichiers ‖ Apps · File manager"                         bind "Apps · Gestionnaire de fichiers"
action "Apps · Yazi (fichiers en terminal) ‖ Apps · Yazi (terminal file manager)"      bind "Apps · Yazi (fichiers en terminal)"
action "Apps · Liste des fenêtres ouvertes ‖ Apps · Open windows list"                 bind "Apps · Liste des fenêtres ouvertes"

# ── Existant : système et session ────────────────────────────
action "Notifs · Ne pas déranger on/off ‖ Notifications · Do not disturb on/off"       bind "Notifs · Ne pas déranger on/off"
action "Notifs · Centre de notifications ‖ Notifications · Notification center"       bind "Notifs · Centre de notifications"
action "Système · Couper / rétablir le micro ‖ System · Mute / unmute microphone"      bind "Média · Couper le micro"
action "Système · Lumière nocturne on/off ‖ System · Night light on/off"               bind "Système · Lumière nocturne on/off"
action "Look · Menu rice (barre + look + stats) ‖ Look · Rice menu (bar + look + stats)" bind "Look · Menu rice (barre + look + stats)"
action "Look · Basculer neon / glass ‖ Look · Toggle neon / glass"                     bind "Look · Basculer neon / glass"
action "Barre · Cacher/afficher ‖ Bar · Hide / show"                                   bind "Barre · Cacher/afficher"
action "Layout · Mode jeu (sans effets) on/off ‖ Layout · Game mode (no effects) on/off" bind "Layout · Mode jeu (sans effets) on/off"
action "Fenêtre · Voir les fenêtres cachées ‖ Window · Show hidden windows"            bind "Fenêtre · Voir les fenêtres cachées"
action "Session · Recharger Hyprland (avec notification) ‖ Session · Reload Hyprland (with notification)" \
    cmd "desk system run reload" \
    "Session · Recharger Hyprland et la barre"
action "Session · Verrouiller ‖ Session · Lock screen"                                 bind "Session · Verrouiller"
action "Session · Menu alimentation ‖ Session · Power menu"                            bind "Session · Menu alimentation"
