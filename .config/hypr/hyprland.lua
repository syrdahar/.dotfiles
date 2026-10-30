-- ──────────────────────────────────────────────────────────────
--  Hyprland — rice "Neon Graffiti" (config Lua, Hyprland ≥ 0.57)
--  Wiki : https://wiki.hypr.land/configuring/
--  API  : /usr/share/hypr/stubs/hl.meta.lua · test : Hyprland --verify-config
--  Transposé de l'ancienne config hyprlang (hyprland.conf) le 2026-10-30 ;
--  sauvegarde : ~/.config/rice-backup-2026-10-30-lua.tar.gz
-- ──────────────────────────────────────────────────────────────

local c = require("colors")


----------------
--- MONITORS ---
----------------

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })

hl.config({
    -- Problème de scaling sur Pycharm
    xwayland = { force_zero_scaling = true },
})


-----------------
--- AUTOSTART ---
-----------------

hl.on("hyprland.start", function()
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE HYPRLAND_INSTANCE_SIGNATURE DISPLAY")
    -- hl.exec_cmd("hyprpaper")   -- → desktop-theme.lua (awww · desk wall)
    hl.exec_cmd("waybar")
    hl.exec_cmd("swaync")
    hl.exec_cmd("swayosd-server")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("~/.config/hypr/scripts/sysnotify.sh")
    -- hl.exec_cmd("wl-paste --type text  --watch cliphist store")   -- → desktop-autostart.lua (filtre des secrets)
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
    hl.exec_cmd("~/.config/hypr/scripts/hyprnight.sh auto")
    hl.exec_cmd("/usr/lib/polkit-kde-authentication-agent-1")
end)


-----------------------------
--- ENVIRONMENT VARIABLES ---
-----------------------------

hl.env("XCURSOR_SIZE", "17")
hl.env("HYPRCURSOR_SIZE", "17")
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")


---------------------
--- LOOK AND FEEL ---
---------------------

hl.config({
    general = {
        gaps_in  = 3,
        gaps_out = 7,

        border_size = 2,

        resize_on_border        = true,
        extend_border_grab_area = 12,
        allow_tearing           = false,

        layout = "dwindle",
    },

    animations = { enabled = true },
})

--        NOM,                               X0,   Y0,      X1,   Y1
hl.curve("easeOutQuint",   { type = "bezier", points = { { 0.23, 1 },    { 0.32, 1 } } })
hl.curve("easeInOutCubic", { type = "bezier", points = { { 0.65, 0.05 }, { 0.36, 1 } } })
hl.curve("spring",         { type = "bezier", points = { { 0.34, 1.36 }, { 0.64, 1 } } })
hl.curve("snappy",         { type = "bezier", points = { { 0.2, 1 },     { 0.3, 1 } } })
hl.curve("linear",         { type = "bezier", points = { { 0, 0 },       { 1, 1 } } })
hl.curve("quick",          { type = "bezier", points = { { 0.15, 0 },    { 0.1, 1 } } })

hl.animation({ leaf = "global",           enabled = true, speed = 4,   bezier = "snappy" })
hl.animation({ leaf = "border",           enabled = true, speed = 4,   bezier = "easeOutQuint" })
hl.animation({ leaf = "borderangle",      enabled = true, speed = 20,  bezier = "easeOutQuint" })
hl.animation({ leaf = "windowsIn",        enabled = true, speed = 3.2, bezier = "spring",       style = "popin 85%" })
hl.animation({ leaf = "windowsOut",       enabled = true, speed = 2,   bezier = "easeOutQuint", style = "popin 85%" })
hl.animation({ leaf = "windowsMove",      enabled = true, speed = 3.2, bezier = "snappy" })
hl.animation({ leaf = "fadeIn",           enabled = true, speed = 2,   bezier = "quick" })
hl.animation({ leaf = "fadeOut",          enabled = true, speed = 1.8, bezier = "quick" })
hl.animation({ leaf = "fadeDim",          enabled = true, speed = 3,   bezier = "quick" })
hl.animation({ leaf = "layersIn",         enabled = true, speed = 2.5, bezier = "snappy",       style = "fade" })
hl.animation({ leaf = "layersOut",        enabled = true, speed = 1.8, bezier = "easeOutQuint", style = "fade" })
hl.animation({ leaf = "workspaces",       enabled = true, speed = 3.2, bezier = "snappy",       style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3,   bezier = "snappy",       style = "slidevert" })
hl.animation({ leaf = "zoomFactor",       enabled = true, speed = 3,   bezier = "quick" })

-- Bordure qui tourne en continu (joli mais consomme GPU/batterie) :
-- hl.animation({ leaf = "borderangle", enabled = true, speed = 60, bezier = "linear", style = "loop" })

-- Look actif (couleurs de bordure, arrondis, opacité, ombre, blur, animations du look) :
-- look.lua → looks/<look>.lua, basculé par scripts/rice.sh look
require("look")

hl.config({
    dwindle = {
        preserve_split = true,
        smart_split    = false,
    },

    master = {
        new_status = "master",
    },

    misc = {
        disable_hyprland_logo        = true,
        disable_splash_rendering     = true,
        background_color             = c.base,
        mouse_move_enables_dpms      = true,
        key_press_enables_dpms       = true,
        animate_manual_resizes       = true,
        animate_mouse_windowdragging = false,
        focus_on_activate            = true,
    },

    cursor = {
        hide_on_key_press = true,
        inactive_timeout  = 5,
    },
})


-------------
--- INPUT ---
-------------

hl.config({
    input = {
        kb_layout  = "fr",
        kb_variant = "",
        kb_model   = "",
        kb_options = "caps:swapescape",
        kb_rules   = "",

        follow_mouse = 1,
        sensitivity  = 0, -- -1.0 - 1.0, 0 means no modification.

        touchpad = {
            natural_scroll       = true,
            disable_while_typing = true,
            tap_to_click         = true,
            scroll_factor        = 0.8,
        },
    },
})

hl.gesture({ fingers = 3, direction = "up",         action = "fullscreen" })
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
hl.gesture({ fingers = 3, direction = "down",       action = "close" })

hl.device({
    name        = "epic-mouse-v1",
    sensitivity = -0.5,
})


-------------------
--- KEYBINDINGS ---
-------------------

-- Tous les raccourcis : keybinds.lua (aide rofi : SUPER+F1)
require("keybinds")


------------------------------
--- WINDOWS AND WORKSPACES ---
------------------------------

hl.window_rule({
    name             = "jetbrains-awt-popup-fix",
    match            = { class = "^(jetbrains-.*)$", title = "^(win[0-9]+)$" },
    no_initial_focus = true,
    float            = true,
})

hl.window_rule({
    -- Ignore maximize requests from all apps.
    name           = "suppress-maximize-events",
    match          = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    -- Fix some dragging issues with XWayland
    name  = "fix-xwayland-drags",
    match = {
        class      = "^$",
        title      = "^$",
        xwayland   = true,
        float      = true,
        fullscreen = false,
        pin        = false,
    },
    no_focus = true,
})

hl.window_rule({
    name  = "move-hyprland-run",
    match = { class = "hyprland-run" },
    move  = "20 monitor_h-120",
    float = true,
})

hl.window_rule({
    -- Petites fenêtres utilitaires en flottant, centrées
    name   = "float-utilities",
    match  = { class = "^(pavucontrol|org.pulseaudio.pavucontrol|blueman-manager|nm-connection-editor|nwg-displays|org.kde.polkit-kde-authentication-agent-1)$" },
    float  = true,
    size   = { 900, 600 },
    center = true,
})

hl.window_rule({
    name   = "float-dialogs",
    match  = { title = "^(Open File|Save As|Open Folder|Choose Files|Ouvrir un fichier|Enregistrer sous|Picture-in-Picture)$" },
    float  = true,
    center = true,
})

hl.window_rule({
    -- Les vidéos/jeux restent opaques
    name   = "opaque-media",
    match  = { class = "^(mpv|vlc|librewolf|firefox|brave-browser|figma-linux)$" },
    opaque = true,
})

-- ── Layers : blur sous la barre, rofi et les notifs ──────────
hl.layer_rule({
    name         = "blur-waybar",
    match        = { namespace = "waybar" },
    blur         = true,
    ignore_alpha = 0.3,
})

hl.layer_rule({
    name         = "blur-rofi",
    match        = { namespace = "rofi" },
    blur         = true,
    ignore_alpha = 0.3,
    animation    = "popin 90%",
})

hl.layer_rule({
    name         = "blur-swaync",
    match        = { namespace = "^(swaync-control-center|swaync-notification-window)$" },
    blur         = true,
    ignore_alpha = 0.3,
})

hl.window_rule({
    -- Tableau de bord cswap ouvert depuis le widget Claude de la barre
    name   = "float-cswap-tui",
    match  = { class = "^(cswap-tui)$" },
    float  = true,
    size   = { 1000, 640 },
    center = true,
})

hl.layer_rule({
    name         = "blur-swayosd",
    match        = { namespace = "swayosd" },
    blur         = true,
    ignore_alpha = 0.3,
})

hl.window_rule({
    -- Notes à la volée (scripts/notes.sh, SUPER+A)
    name      = "notes-scratchpad",
    match     = { class = "^(notes-scratch)$" },
    workspace = "special:notes silent",
    float     = true,
    size      = "monitor_w*0.5 monitor_h*0.6",
    center    = true,
})

hl.window_rule({
    -- Fenêtres cachées (SUPER+E) : on les voit flotter quand on ouvre le tiroir
    name    = "hidden-drawer",
    match   = { workspace = "special:hidden" },
    opacity = "0.9",
})

hl.window_rule({
    -- btop ouvert depuis les modules CPU / RAM de la barre
    name   = "float-btop",
    match  = { class = "^(btop-float)$" },
    float  = true,
    size   = "monitor_w*0.6 monitor_h*0.65",
    center = true,
})

-- ── Command center (~/.local/bin/desktop) ──
require("desktop-binds")
require("desktop-leader")
require("desktop-rules")
require("desktop-autostart")
require("desktop-dictation")
require("desktop-monitors")

require("desktop-theme")   -- fond d'écran (awww) + thème auto (desk theme)
