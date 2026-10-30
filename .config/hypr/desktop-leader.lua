-- ──────────────────────────────────────────────────────────────
--  Command center — submap "leader" (SUPER+Espace, puis UNE touche)
--
--  Chaque lettre lance "desk leader <module>" : le script quitte le leader
--  puis lance l'action. La notification which-key liste les binds décrits
--  ci-dessous (lus dans hyprctl binds) et se ferme toute seule.
--
--  Ordre important (KeybindManager) :
--   1. modificateurs seuls → submap("leader") (ne rien faire) : sinon le
--      catchall annulerait le leader dès qu'on appuie sur SUPER ;
--   2. les actions ;
--   3. catchall EN DERNIER : toute autre touche est avalée et ferme le leader
--      (il se déclenche aussi après une action, ce qui ferme le leader).
--  Les variantes « SUPER encore enfoncé » sont des binds sans description
--  (masquées de la cheatsheet et de la notification).
-- ──────────────────────────────────────────────────────────────

local H    = require("helpers")
local dsp  = hl.dsp
local desk = "~/.local/bin/desktop/desk"

-- touche, description, module lancé par « desk leader … »
local LEADER = {
    { "space", "Palette · Palette de commandes ‖ Palette · Command palette",                                          "palette" },
    { "H", "Aide · Cheatsheet de tous les raccourcis ‖ Help · Cheatsheet of all shortcuts",                          "cheatsheet" },
    { "T", "Scratchpad · Terminal (tmux) afficher/cacher ‖ Scratchpad · Toggle terminal (tmux)",                     "scratch term" },
    { "B", "Scratchpad · btop afficher/cacher ‖ Scratchpad · Toggle btop",                                           "scratch btop" },
    { "C", "Presse-papier · Actions selon le contenu copié ‖ Clipboard · Actions for copied content",               "clip" },
    { "Q", "Calcul · Calculatrice et conversions (qalc) ‖ Calc · Calculator and unit conversions (qalc)",           "calc" },
    { "G", "Git · Menu git du dossier courant ‖ Git · Git menu for current directory",                              "git" },
    { "E", "Projet · Ouvrir / rejoindre un projet ‖ Project · Open / switch to a project",                          "project" },
    { "P", "PDF · Boîte à outils PDF (fusionner · signer · compresser…) ‖ PDF · PDF toolbox (merge · sign · compress…)", "pdf" },
    { "D", "Docker · Conteneurs ‖ Docker · Containers",                                                             "docker" },
    { "K", "Ports · Ports en écoute et processus ‖ Ports · Listening ports and processes",                          "ports" },
    { "S", "SSH · Se connecter à un hôte ‖ SSH · Connect to a host",                                                "ssh" },
    { "W", "Web · Recherche (gh mdn npm aur so…) ‖ Web · Search (gh mdn npm aur so…)",                              "web" },
    { "M", "Mobile · scrcpy / émulateur / adb ‖ Mobile · scrcpy / emulator / adb",                                  "mobile" },
    { "R", "Capture · Captures (OCR · annotation · vidéo…) ‖ Screenshot · Captures (OCR · annotate · video…)",      "capture" },
    { "A", "IA · Claude sur le presse-papier (expliquer · corriger · tests…) ‖ AI · Claude on clipboard (explain · fix · tests…)", "ai" },
    { "I", "IA · ChatGPT question rapide (calcul · conversion · info) ‖ AI · ChatGPT quick question (math · conversion · facts)", "gpt" },
    { "U", "Processus · Par CPU / RAM (tuer · inspecter) ‖ Processes · By CPU / RAM (kill · inspect)",              "procs" },
    { "X", "Système · Audio · Wi-Fi · Bluetooth · VPN · session ‖ System · Audio · Wi-Fi · Bluetooth · VPN · session", "system" },
    { "N", "Notes · Notes et TODO (~/notes) ‖ Notes · Notes and TODOs (~/notes)",                                   "notes" },
    { "Z", "Focus · Minuteur · pomodoro · mode focus ‖ Focus · Timer · pomodoro · focus mode",                     "focus" },
    { "L", "Langue · Basculer français / anglais ‖ Language · Toggle French / English",                             "lang toggle" },
    { "O", "Notifs · Claude Code (on/off · test) ‖ Notifications · Claude Code (on/off · test)",                    "claudenotify" },
    { "F", "Drive · Proton Drive (parcourir · envoyer · lien) ‖ Drive · Proton Drive (browse · upload · link)",     "drive" },
    { "V", "Drop · Partage réseau local (texte · fichiers · QR) ‖ Drop · LAN sharing (text · files · QR)",          "drop" },
    { "Y", "Thème · Fond d'écran · palette · look ‖ Theme · Wallpaper · palette · look",                            "theme" },
}

H.submap("leader", function()
    -- 1. modificateurs seuls : rester dans le leader
    for _, k in ipairs({ "Super_L", "Super_R", "SUPER + Super_L", "SUPER + Super_R", "Shift_L", "Shift_R" }) do
        H.bind(k, dsp.submap("leader"))
    end

    -- 2. actions (décrites → notification which-key, cheatsheet, palette)
    for _, l in ipairs(LEADER) do
        H.bindd(l[1], l[2], desk .. " leader " .. l[3])
    end
    H.bindd("escape", "Leader · Annuler ‖ Leader · Cancel", dsp.submap("reset"))

    -- mêmes actions, SUPER encore enfoncé (sans description)
    for _, l in ipairs(LEADER) do
        H.bind("SUPER + " .. l[1], desk .. " leader " .. l[3])
    end
    H.bind("SUPER + escape", dsp.submap("reset"))

    -- 3. toute autre touche : ferme le leader (EN DERNIER)
    H.bind("catchall", dsp.submap("reset"))
    H.bind("SUPER + catchall", dsp.submap("reset"))
end)
