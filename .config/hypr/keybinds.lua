-- ──────────────────────────────────────────────────────────────
--  Raccourcis — gestion des fenêtres façon chadwm (config.def.h)
--  adaptée à Hyprland + AZERTY ; tes raccourcis d'apps gardent
--  la priorité (SUPER+D/Q/M/V).
--
--  Tous déclarés avec bindd (avec description) → l'aide rofi
--  (SUPER+F1 ou SUPER+!) est générée automatiquement depuis la config.
--  Format : bindd("MODS + touche", "Catégorie · description", action, options)
--    action = commande shell (chaîne), dispatcher hl.dsp.* ou fonction Lua
--    options : { repeating = true } (ex-bindde), { locked = true } (ex-binddl),
--              { mouse = true } (ex-binddm)
-- ──────────────────────────────────────────────────────────────

local H     = require("helpers")
local P     = require("programs")
local bindd = H.bindd
local dsp   = hl.dsp

local S    = "~/.config/hypr/scripts"
local wm   = S .. "/wm.sh"
local osd  = S .. "/osd.sh"
local rice = S .. "/rice.sh"

local REP    = { repeating = true }
local LOCKED = { locked = true }
local LOCKED_REP = { locked = true, repeating = true }

-- ── Aide ─────────────────────────────────────────────────────
bindd("SUPER + F1",     "Aide · Afficher tous les raccourcis", "pkill rofi || " .. S .. "/keybinds.sh")
bindd("SUPER + exclam", "Aide · Afficher tous les raccourcis", "pkill rofi || " .. S .. "/keybinds.sh")

-- ── Applications ─────────────────────────────────────────────
bindd("SUPER + Return",      "Apps · Terminal",                        P.terminal)
bindd("SUPER + D",           "Apps · Lanceur d'applications",          "pkill rofi || " .. P.menu)
bindd("SUPER + C",           "Apps · Lanceur d'applications (chadwm)", "pkill rofi || " .. P.menu)
bindd("SUPER + ALT + E",     "Apps · Gestionnaire de fichiers",        P.fileManager)
bindd("SUPER + P",           "Apps · Yazi (fichiers en terminal)",     P.terminal .. " -e yazi")
bindd("SUPER + M",           "Apps · Navigateur",                      P.browser)
bindd("SUPER + ALT + Tab",   "Apps · Liste des fenêtres ouvertes",     "pkill rofi || rofi -show window")
bindd("SUPER + SHIFT + V",   "Apps · Historique du presse-papier",     "pkill rofi || " .. P.clipboard)
bindd("SUPER + SHIFT + X",   "Apps · Pipette de couleur",              S .. "/colorpicker.sh")

-- ── Notes ────────────────────────────────────────────────────
bindd("SUPER + A",           "Notes · Ouvrir/cacher le scratchpad",    S .. "/notes.sh toggle")
bindd("SUPER + SHIFT + A",   "Notes · Ajouter une ligne rapide",       "pkill rofi || " .. S .. "/notes.sh quick")

-- ── Session ──────────────────────────────────────────────────
local quit = "command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"
bindd("SUPER + Q",           "Session · Verrouiller",                    P.lockscreen)
bindd("SUPER + Escape",      "Session · Menu alimentation",              "pkill rofi || " .. P.powermenu)
bindd("SUPER + SHIFT + R",   "Session · Recharger Hyprland et la barre", "hyprctl reload && " .. wm .. " reapply && pkill -SIGUSR2 waybar")
bindd("SUPER + CTRL + Q",    "Session · Quitter Hyprland",               quit)
bindd("SUPER + SHIFT + C",   "Session · Quitter Hyprland",               quit)

-- ── Notifications ────────────────────────────────────────────
bindd("SUPER + N",           "Notifs · Ne pas déranger on/off",    S .. "/dnd.sh")
bindd("SUPER + SHIFT + N",   "Notifs · Centre de notifications",   "swaync-client -t -sw")
bindd("SUPER + ALT + N",     "Système · Lumière nocturne on/off",  S .. "/hyprnight.sh toggle")

-- ── Barre & look ─────────────────────────────────────────────
bindd("SUPER + B",           "Barre · Cacher/afficher",                      "pkill -SIGUSR1 waybar")
bindd("SUPER + CTRL + B",    "Barre · Mode suivant (îles/flottante/collée)", rice .. " bar next")
bindd("SUPER + SHIFT + B",   "Look · Basculer neon / glass",                 rice .. " look toggle")
bindd("SUPER + ALT + B",     "Look · Menu rice (barre + look + stats)",      "pkill rofi || " .. rice .. " menu")
bindd("SUPER + ALT + S",     "Barre · Basculer usage Claude / CPU-RAM",      rice .. " stats toggle")

-- ── Fenêtres (chadwm) ────────────────────────────────────────
bindd("SUPER + SHIFT + Q",       "Fenêtre · Fermer",                              dsp.window.close())
bindd("SUPER + V",               "Fenêtre · Flottante/tuilée",                    dsp.window.float())
bindd("SUPER + SHIFT + space",   "Fenêtre · Flottante/tuilée (chadwm)",           dsp.window.float())
bindd("SUPER + F",               "Fenêtre · Plein écran",                         dsp.window.fullscreen({ mode = "fullscreen" }))
bindd("SUPER + ALT + F",         "Fenêtre · Maximiser (garde la barre)",          dsp.window.fullscreen({ mode = "maximized" }))
bindd("SUPER + J",               "Fenêtre · Focus suivante",                      dsp.window.cycle_next())
bindd("SUPER + K",               "Fenêtre · Focus précédente",                    dsp.window.cycle_next({ next = false }))
bindd("SUPER + SHIFT + J",       "Fenêtre · Échanger avec la suivante",           dsp.window.swap({ next = true }))
bindd("SUPER + SHIFT + K",       "Fenêtre · Échanger avec la précédente",         dsp.window.swap({ prev = true }))
bindd("SUPER + SHIFT + Return",  "Fenêtre · Zoom (passer en principale)",         wm .. " zoom")
bindd("SUPER + H",               "Fenêtre · Réduire la zone principale (mfact)",  wm .. " mfact -0.05", REP)
bindd("SUPER + L",               "Fenêtre · Agrandir la zone principale (mfact)", wm .. " mfact +0.05", REP)
bindd("SUPER + SHIFT + H",       "Fenêtre · Agrandir dans la pile (cfact)",       wm .. " cfact 40", REP)
bindd("SUPER + SHIFT + L",       "Fenêtre · Réduire dans la pile (cfact)",        wm .. " cfact -40", REP)
bindd("SUPER + SHIFT + O",       "Fenêtre · Réinitialiser les proportions",       wm .. " mfact reset")
bindd("SUPER + I",               "Fenêtre · +1 fenêtre en zone master",           wm .. " nmaster +")
bindd("SUPER + ALT + D",         "Fenêtre · −1 fenêtre en zone master",           wm .. " nmaster -")
bindd("SUPER + E",               "Fenêtre · Cacher (minimiser)",                  wm .. " hide")
bindd("SUPER + SHIFT + E",       "Fenêtre · Restaurer la dernière cachée",        wm .. " restore")
bindd("SUPER + CTRL + E",        "Fenêtre · Voir les fenêtres cachées",           wm .. " hidden")
bindd("SUPER + CTRL + W",        "Fenêtre · Onglets : grouper/dégrouper",         dsp.group.toggle())
bindd("SUPER + CTRL + Tab",      "Fenêtre · Onglets : suivant",                   dsp.group.next())
bindd("SUPER + CTRL + SHIFT + Tab", "Fenêtre · Onglets : précédent",              dsp.group.prev())
bindd("SUPER + ALT + W",         "Fenêtre · Onglets : sortir du groupe",          dsp.window.move({ out_of_group = true }))
bindd("SUPER + ALT + J",         "Fenêtre · Changer le sens du découpage",        dsp.layout("togglesplit"))
bindd("SUPER + ALT + K",         "Fenêtre · Inverser les deux moitiés",           dsp.layout("swapsplit"))
bindd("SUPER + ALT + C",         "Fenêtre · Centrer (flottante)",                 dsp.window.center())
bindd("SUPER + ALT + P",         "Fenêtre · Pseudo-tuilage",                      dsp.window.pseudo())
bindd("SUPER + CTRL + P",        "Fenêtre · Épingler sur tous les workspaces",    dsp.window.pin())
bindd("SUPER + ALT + V",         "Fenêtre · Mode picture-in-picture",             wm .. " pip")
bindd("SUPER + ALT + O",         "Fenêtre · Opacité forcée on/off",               dsp.window.set_prop({ prop = "opaque", value = "toggle" }))
bindd("SUPER + twosuperior",     "Fenêtre · Focus urgente ou précédente",         dsp.focus({ urgent_or_last = true }))

-- Focus / déplacement / redimensionnement directionnels
bindd("SUPER + up",             "Fenêtre · Focus en haut",       dsp.focus({ direction = "up" }))
bindd("SUPER + down",           "Fenêtre · Focus en bas",        dsp.focus({ direction = "down" }))
bindd("SUPER + ALT + left",     "Fenêtre · Focus à gauche",      dsp.focus({ direction = "left" }))
bindd("SUPER + ALT + right",    "Fenêtre · Focus à droite",      dsp.focus({ direction = "right" }))
bindd("SUPER + ALT + up",       "Fenêtre · Focus en haut",       dsp.focus({ direction = "up" }))
bindd("SUPER + ALT + down",     "Fenêtre · Focus en bas",        dsp.focus({ direction = "down" }))
bindd("SUPER + SHIFT + left",   "Fenêtre · Déplacer à gauche",   dsp.window.move({ direction = "left" }))
bindd("SUPER + SHIFT + right",  "Fenêtre · Déplacer à droite",   dsp.window.move({ direction = "right" }))
bindd("SUPER + SHIFT + up",     "Fenêtre · Déplacer en haut",    dsp.window.move({ direction = "up" }))
bindd("SUPER + SHIFT + down",   "Fenêtre · Déplacer en bas",     dsp.window.move({ direction = "down" }))
bindd("SUPER + CTRL + left",    "Fenêtre · Rétrécir en largeur", dsp.window.resize({ x = -40, y = 0, relative = true }), REP)
bindd("SUPER + CTRL + right",   "Fenêtre · Élargir",             dsp.window.resize({ x = 40, y = 0, relative = true }), REP)
bindd("SUPER + CTRL + up",      "Fenêtre · Rétrécir en hauteur", dsp.window.resize({ x = 0, y = -40, relative = true }), REP)
bindd("SUPER + CTRL + down",    "Fenêtre · Agrandir en hauteur", dsp.window.resize({ x = 0, y = 40, relative = true }), REP)
bindd("SUPER + R",              "Fenêtre · Mode redimensionnement (Échap)", H.enter_submap("resize"))

-- Souris
-- Zoom écran : facteur × ou ÷ 1.25 (jamais sous 1)
local function zoom(factor)
    return function()
        local z = hl.get_config("cursor.zoom_factor") or 1
        hl.config({ cursor = { zoom_factor = math.max(z * factor, 1) } })
    end
end
bindd("SUPER + mouse:272",        "Souris · Déplacer la fenêtre",      dsp.window.drag(),   { mouse = true })
bindd("SUPER + mouse:273",        "Souris · Redimensionner la fenêtre", dsp.window.resize(), { mouse = true })
bindd("SUPER + mouse:274",        "Souris · Flottante/tuilée",         dsp.window.float())
bindd("SUPER + mouse_down",       "Workspace · Suivant (molette)",     dsp.focus({ workspace = "e+1" }))
bindd("SUPER + mouse_up",         "Workspace · Précédent (molette)",   dsp.focus({ workspace = "e-1" }))
bindd("SUPER + ALT + mouse_down", "Écran · Zoom avant",                zoom(1.25))
bindd("SUPER + ALT + mouse_up",   "Écran · Zoom arrière",              zoom(1 / 1.25))

-- ── Layouts (chadwm) ─────────────────────────────────────────
bindd("SUPER + T",               "Layout · Tile (master-stack)",           wm .. " layout master")
bindd("SUPER + SHIFT + F",       "Layout · Monocle",                       wm .. " layout monocle")
bindd("SUPER + ALT + M",         "Layout · Spirale (dwindle · par défaut)", wm .. " layout dwindle")
bindd("SUPER + CTRL + G",        "Layout · Grille 2×2 (dwindle)",          wm .. " layout dwindle")
bindd("SUPER + CTRL + S",        "Layout · Défilant (scrolling)",          wm .. " layout scrolling")
bindd("SUPER + CTRL + space",    "Layout · Revenir au précédent",          wm .. " layout prev")
bindd("SUPER + CTRL + comma",    "Layout · Précédent dans la liste",       wm .. " layout cycle-")
bindd("SUPER + CTRL + semicolon", "Layout · Suivant dans la liste",        wm .. " layout cycle+")
bindd("SUPER + CTRL + SHIFT + T", "Layout · Tout le workspace flottant/tuilé", wm .. " allfloat")
bindd("SUPER + ALT + G",         "Layout · Mode jeu (sans effets) on/off", wm .. " gamemode")

-- ── Gaps (chadwm ; 6-9 = touches - è _ ç en AZERTY) ─────────
bindd("SUPER + CTRL + T",               "Gaps · Activer/désactiver",              wm .. " gaps toggle")
bindd("SUPER + CTRL + I",               "Gaps · Tous +",                          wm .. " gaps all 1", REP)
bindd("SUPER + CTRL + D",               "Gaps · Tous −",                          wm .. " gaps all -1", REP)
bindd("SUPER + SHIFT + I",              "Gaps · Intérieurs +",                    wm .. " gaps inner 1", REP)
bindd("SUPER + CTRL + SHIFT + I",       "Gaps · Intérieurs −",                    wm .. " gaps inner -1", REP)
bindd("SUPER + CTRL + O",               "Gaps · Extérieurs +",                    wm .. " gaps outer 1", REP)
bindd("SUPER + CTRL + SHIFT + O",       "Gaps · Extérieurs −",                    wm .. " gaps outer -1", REP)
bindd("SUPER + CTRL + minus",           "Gaps · Intérieurs horizontaux +",        wm .. " gaps ih 1", REP)
bindd("SUPER + CTRL + SHIFT + minus",   "Gaps · Intérieurs horizontaux −",        wm .. " gaps ih -1", REP)
bindd("SUPER + CTRL + egrave",          "Gaps · Intérieurs verticaux +",          wm .. " gaps iv 1", REP)
bindd("SUPER + CTRL + SHIFT + egrave",  "Gaps · Intérieurs verticaux −",          wm .. " gaps iv -1", REP)
bindd("SUPER + CTRL + underscore",      "Gaps · Extérieurs horizontaux +",        wm .. " gaps oh 1", REP)
bindd("SUPER + CTRL + SHIFT + underscore", "Gaps · Extérieurs horizontaux −",     wm .. " gaps oh -1", REP)
bindd("SUPER + CTRL + ccedilla",        "Gaps · Extérieurs verticaux +",          wm .. " gaps ov 1", REP)
bindd("SUPER + CTRL + SHIFT + ccedilla", "Gaps · Extérieurs verticaux −",         wm .. " gaps ov -1", REP)
bindd("SUPER + CTRL + SHIFT + D",       "Gaps · Valeurs par défaut",              wm .. " gaps default")

-- ── Bordures (chadwm) ────────────────────────────────────────
bindd("SUPER + SHIFT + parenright", "Bordure · Plus fine (touche à la place du - QWERTY)", wm .. " border -1", REP)
bindd("SUPER + SHIFT + P",          "Bordure · Plus épaisse",                               wm .. " border 1", REP)
bindd("SUPER + SHIFT + W",          "Bordure · Épaisseur par défaut",                       wm .. " border default")

-- ── Workspaces & écrans ──────────────────────────────────────
bindd("SUPER + left",              "Workspace · Précédent (chadwm)",     dsp.focus({ workspace = "r-1" }))
bindd("SUPER + right",             "Workspace · Suivant (chadwm)",       dsp.focus({ workspace = "r+1" }))
bindd("SUPER + Tab",               "Workspace · Revenir au dernier",     dsp.focus({ workspace = "previous" }))
bindd("SUPER + S",                 "Workspace · Scratchpad afficher/cacher", dsp.workspace.toggle_special("magic"))
bindd("SUPER + SHIFT + S",         "Workspace · Envoyer au scratchpad",  dsp.window.move({ workspace = "special:magic" }))
bindd("SUPER + comma",             "Écran · Focus écran précédent",      dsp.focus({ monitor = "-1" }))
bindd("SUPER + semicolon",         "Écran · Focus écran suivant",        dsp.focus({ monitor = "+1" }))
bindd("SUPER + SHIFT + comma",     "Écran · Envoyer la fenêtre à l'écran précédent", dsp.window.move({ monitor = "-1" }))
bindd("SUPER + SHIFT + semicolon", "Écran · Envoyer la fenêtre à l'écran suivant",   dsp.window.move({ monitor = "+1" }))

-- Rangée des chiffres AZERTY : & é " ' ( - è _ ç à = workspaces 1 à 10
local WS_KEYS = { "ampersand", "eacute", "quotedbl", "apostrophe", "parenleft",
                  "minus", "egrave", "underscore", "ccedilla", "agrave" }

for i, key in ipairs(WS_KEYS) do
    bindd("SUPER + " .. key, "Workspace · Aller au " .. i, dsp.focus({ workspace = i }))
end

for i, key in ipairs(WS_KEYS) do
    bindd("SUPER + SHIFT + " .. key, "Workspace · Envoyer la fenêtre au " .. i,
          dsp.window.move({ workspace = i, follow = false }))
end

-- Extra : CTRL+chiffre = emmener la fenêtre ET la suivre
for i = 1, 5 do
    bindd("SUPER + CTRL + " .. WS_KEYS[i], "Workspace · Emmener la fenêtre au " .. i,
          dsp.window.move({ workspace = i }))
end

-- ── Captures ─────────────────────────────────────────────────
local shot = "~/.local/bin/desktop/desk-shot"
bindd("Print",                           "Capture · Zone (fichier)",         "hyprshot -m region -s -- " .. shot)
bindd("SHIFT + Print",                   "Capture · Écran entier (fichier)", "hyprshot -m output -s -- " .. shot)
bindd("SUPER + Print",                   "Capture · Fenêtre (fichier)",      "hyprshot -m window -s -- " .. shot)
bindd("XF86SelectiveScreenshot",         "Capture · Zone (fichier)",         "hyprshot -m region -s -- " .. shot)
bindd("SHIFT + XF86SelectiveScreenshot", "Capture · Écran entier (fichier)", "hyprshot -m output -s -- " .. shot)
bindd("SUPER + XF86SelectiveScreenshot", "Capture · Fenêtre (fichier)",      "hyprshot -m window -s -- " .. shot)
bindd("SUPER + U",                       "Capture · Zone → presse-papier (chadwm)",  "hyprshot -m region --clipboard-only")
bindd("SUPER + CTRL + U",                "Capture · Écran → presse-papier (chadwm)", "hyprshot -m output --clipboard-only")

-- ── Multimédia (OSD swayosd) ─────────────────────────────────
bindd("XF86AudioRaiseVolume",  "Média · Volume +",         osd .. " vol-up",   LOCKED_REP)
bindd("XF86AudioLowerVolume",  "Média · Volume −",         osd .. " vol-down", LOCKED_REP)
bindd("XF86AudioMute",         "Média · Couper le son",    osd .. " vol-mute", LOCKED)
bindd("XF86AudioMicMute",      "Média · Couper le micro",  osd .. " mic-mute", LOCKED)
bindd("XF86MonBrightnessUp",   "Média · Luminosité +",     osd .. " bri-up",   LOCKED_REP)
bindd("XF86MonBrightnessDown", "Média · Luminosité −",     osd .. " bri-down", LOCKED_REP)
bindd("XF86AudioNext",         "Média · Piste suivante",   "playerctl next",       LOCKED)
bindd("XF86AudioPause",        "Média · Lecture/pause",    "playerctl play-pause", LOCKED)
bindd("XF86AudioPlay",         "Média · Lecture/pause",    "playerctl play-pause", LOCKED)
bindd("XF86AudioPrev",         "Média · Piste précédente", "playerctl previous",   LOCKED)

-- ── Sous-mode redimensionnement (SUPER+R, Échap pour sortir) ─
H.submap("resize", function()
    bindd("right",  "Redim · Élargir",             dsp.window.resize({ x = 30, y = 0, relative = true }), REP)
    bindd("left",   "Redim · Rétrécir",            dsp.window.resize({ x = -30, y = 0, relative = true }), REP)
    bindd("up",     "Redim · Rétrécir en hauteur", dsp.window.resize({ x = 0, y = -30, relative = true }), REP)
    bindd("down",   "Redim · Agrandir en hauteur", dsp.window.resize({ x = 0, y = 30, relative = true }), REP)
    bindd("L",      "Redim · Élargir",             dsp.window.resize({ x = 30, y = 0, relative = true }), REP)
    bindd("H",      "Redim · Rétrécir",            dsp.window.resize({ x = -30, y = 0, relative = true }), REP)
    bindd("K",      "Redim · Rétrécir en hauteur", dsp.window.resize({ x = 0, y = -30, relative = true }), REP)
    bindd("J",      "Redim · Agrandir en hauteur", dsp.window.resize({ x = 0, y = 30, relative = true }), REP)
    bindd("escape", "Redim · Quitter le mode",     dsp.submap("reset"))
    bindd("Return", "Redim · Quitter le mode",     dsp.submap("reset"))
end)
