# shellcheck shell=bash
# ──────────────────────────────────────────────────────────────
#  Actions de la palette (SUPER+X, ou SUPER+Espace puis Espace).
#  Une ligne = une action, dans l'ordre d'affichage :
#
#   action "Catégorie · Libellé" cmd  "commande shell"  ["description d'un bind"]
#   action "Catégorie · Libellé" bind "description exacte d'un bindd"
#
#  Le raccourci affiché à droite est retrouvé tout seul dans `hyprctl binds` :
#   - bind : le(s) bind(s) qui portent cette description (on exécute ce bind) ;
#   - cmd  : le(s) bind(s) exec qui lancent la même commande
#            ("desk x" ≡ "~/.local/bin/desktop/desk x" ≡ "desk leader x"),
#            ou ceux qui portent la description donnée en 4e argument.
#  Dans une commande, `desk` est dans le PATH.
# ──────────────────────────────────────────────────────────────

# ── Command center ───────────────────────────────────────────
action "Aide · Cheatsheet de tous les raccourcis"      cmd  "desk cheatsheet"
action "Aide · Liste des raccourcis (keybinds.sh)"     bind "Aide · Afficher tous les raccourcis"
action "Scratchpad · Terminal (tmux)"                  cmd  "desk scratch term"
action "Scratchpad · btop"                             cmd  "desk scratch btop"
action "Scratchpad · Notes (nvim)"                     bind "Notes · Ouvrir/cacher le scratchpad"
action "Scratchpad · Magic (afficher/cacher)"          bind "Workspace · Scratchpad afficher/cacher"
action "Scratchpad · Envoyer la fenêtre dans Magic"    bind "Workspace · Envoyer au scratchpad"

# ── Presse-papier (desk clip) ────────────────────────────────
action "Presse-papier · Actions selon le contenu copié" cmd  "desk clip"
action "Presse-papier · Historique"                    bind "Apps · Historique du presse-papier"
action "Calcul · Calculatrice et conversions (qalc)"   cmd  "desk calc"
# toutes les actions de desk-clip (URL, JSON, JWT, texte, générateurs…), lues dans le script
while IFS=$'\t' read -r id label; do
    [[ $id == calc || $id == history ]] && continue          # déjà listées au-dessus
    case $label in
        Générer*) action "$label" cmd "desk clip run $id" ;;
        Outils*)  action "Presse-papier · ${label#Outils · }" cmd "desk clip run $id" ;;
        *)        action "Presse-papier · $label" cmd "desk clip run $id" ;;
    esac
done < <("$DESK_DIR/desk-clip" --list)

# ── Dev (phase 3) ────────────────────────────────────────────
action "Projet · Ouvrir / rejoindre un projet"         cmd  "desk project"
action "Git · Menu git du dossier courant"             cmd  "desk git"
action "Docker · Conteneurs"                           cmd  "desk docker"
action "Ports · Ports en écoute et processus"          cmd  "desk ports"
action "SSH · Se connecter à un hôte"                  cmd  "desk ssh"
action "Web · Recherche (gh mdn npm aur so…)"          cmd  "desk web"
action "Mobile · scrcpy / émulateur / adb"             cmd  "desk mobile"
# sous-actions de chaque module, lues dans les scripts (desk-<module> --list)
for mod in project git docker ports mobile; do
    while IFS=$'\t' read -r id label; do
        case "$mod:$id" in project:pick|docker:containers|ports:ports) continue ;; esac   # = menus ci-dessus
        action "$label" cmd "desk $mod run $id"
    done < <("$DESK_DIR/desk-$mod" --list)
done

# ── Existant : notes, captures ───────────────────────────────
action "Notes · Ajouter une ligne rapide"              bind "Notes · Ajouter une ligne rapide"
action "Capture · Zone → fichier"                      bind "Capture · Zone (fichier)"
action "Capture · Fenêtre → fichier"                   bind "Capture · Fenêtre (fichier)"
action "Capture · Écran entier → fichier"              bind "Capture · Écran entier (fichier)"
action "Capture · Zone → presse-papier"                bind "Capture · Zone → presse-papier (chadwm)"
action "Capture · Écran → presse-papier"               bind "Capture · Écran → presse-papier (chadwm)"
action "Couleur · Pipette (hexa copié)"                bind "Apps · Pipette de couleur"

# ── Existant : applications ──────────────────────────────────
action "Apps · Terminal"                               bind "Apps · Terminal"
action "Apps · Lanceur d'applications"                 bind "Apps · Lanceur d'applications"
action "Apps · Navigateur"                             bind "Apps · Navigateur"
action "Apps · Gestionnaire de fichiers"               bind "Apps · Gestionnaire de fichiers"
action "Apps · Yazi (fichiers en terminal)"            bind "Apps · Yazi (fichiers en terminal)"
action "Apps · Liste des fenêtres ouvertes"            bind "Apps · Liste des fenêtres ouvertes"

# ── Existant : système et session ────────────────────────────
action "Notifs · Ne pas déranger on/off"               bind "Notifs · Ne pas déranger on/off"
action "Notifs · Centre de notifications"              bind "Notifs · Centre de notifications"
action "Système · Couper / rétablir le micro"          bind "Média · Couper le micro"
action "Système · Lumière nocturne on/off"             bind "Système · Lumière nocturne on/off"
action "Look · Menu rice (barre + look + stats)"       bind "Look · Menu rice (barre + look + stats)"
action "Look · Basculer neon / glass"                  bind "Look · Basculer neon / glass"
action "Barre · Cacher/afficher"                       bind "Barre · Cacher/afficher"
action "Layout · Mode jeu (sans effets) on/off"        bind "Layout · Mode jeu (sans effets) on/off"
action "Fenêtre · Voir les fenêtres cachées"           bind "Fenêtre · Voir les fenêtres cachées"
action "Session · Recharger Hyprland (avec notification)" \
    cmd "hyprctl reload >/dev/null && ~/.config/hypr/scripts/wm.sh reapply; pkill -SIGUSR2 waybar; e=\$(hyprctl configerrors | grep -v '^\s*\$' || true); if [[ -z \$e ]]; then notify-send -a desk -u low -i view-refresh-symbolic 'Config rechargée' 'Aucune erreur'; else notify-send -a desk -u critical -i dialog-error-symbolic 'Config rechargée avec erreurs' \"\$e\"; fi" \
    "Session · Recharger Hyprland et la barre"
action "Session · Verrouiller"                         bind "Session · Verrouiller"
action "Session · Menu alimentation"                   bind "Session · Menu alimentation"
