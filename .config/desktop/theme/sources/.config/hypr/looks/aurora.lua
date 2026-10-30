-- ──────────────────────────────────────────────────────────────
--  Look "aurora" : fenêtres translucides, bordure dégradée qui tourne, ombre lumineuse teintée accent, blur moyen
--  Activé via ~/.config/hypr/look.lua → looks/aurora.lua (rice.sh look aurora)
--  Chargé APRÈS les animations de hyprland.lua : la rotation de bordure ci-dessous les remplace.
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/aurora.lua
-- ──────────────────────────────────────────────────────────────

local c = require("colors")

hl.config({
    general = {
        col = {
            active_border   = { colors = { c.cyan, c.magenta, c.gold }, angle = 45 },
            inactive_border = "rgba(49345988)",
        },
    },

    decoration = {
        rounding       = 14,
        rounding_power = 2.5,

        active_opacity   = 0.92,
        inactive_opacity = 0.85,

        dim_inactive = true,
        dim_strength = 0.05,

        shadow = {
            enabled        = true,
            range          = 30,
            render_power   = 3,
            offset         = { 0, 0 },
            color          = "rgba(c23d9e55)",
            color_inactive = "rgba(29b4d722)",
        },

        blur = {
            enabled           = true,
            size              = 8,
            passes            = 3,
            new_optimizations = true,
            ignore_opacity    = true,
            xray              = false,
            noise             = 0.015,
            contrast          = 1.05,
            brightness        = 0.95,
            vibrancy          = 0.3,
            vibrancy_darkness = 0.2,
            popups            = true,
        },
    },
})

-- Fait tourner la bordure dégradée en boucle (look aurora uniquement)
hl.animation({ leaf = "borderangle", enabled = true, speed = 100, bezier = "linear", style = "loop" })
