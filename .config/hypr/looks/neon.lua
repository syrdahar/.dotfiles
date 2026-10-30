-- ──────────────────────────────────────────────────────────────
--  Look "neon" : fenêtres opaques, bordure néon, blur léger
--  Activé via ~/.config/hypr/look.lua → looks/neon.lua (rice.sh look neon)
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/neon.lua
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
        rounding       = 12,
        rounding_power = 2.5,

        active_opacity   = 1.0,
        inactive_opacity = 0.94,

        dim_inactive = true,
        dim_strength = 0.06,

        shadow = {
            enabled        = true,
            range          = 22,
            render_power   = 3,
            offset         = { 0, 6 },
            color          = "rgba(06040ecc)",
            color_inactive = "rgba(06040e88)",
        },

        blur = {
            enabled           = true,
            size              = 7,
            passes            = 3,
            new_optimizations = true,
            ignore_opacity    = true,
            xray              = false,
            noise             = 0.015,
            contrast          = 1.05,
            brightness        = 0.95,
            vibrancy          = 0.25,
            vibrancy_darkness = 0.2,
            popups            = true,
        },
    },
})
