-- ──────────────────────────────────────────────────────────────
--  Look "glass" : verre dépoli néomorphique — fenêtres translucides + gros blur, liseré clair façon arête de verre, ombres longues et douces
--  Activé via ~/.config/hypr/look.lua → looks/glass.lua (rice.sh look glass)
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/glass.lua
-- ──────────────────────────────────────────────────────────────

hl.config({
    general = {
        col = {
            active_border   = { colors = { "rgba(e6ddf066)", "rgba(29b4d799)", "rgba(c23d9e99)" }, angle = 45 },
            inactive_border = "rgba(e6ddf01c)",
        },
    },

    decoration = {
        rounding       = 14,
        rounding_power = 3,

        active_opacity   = 0.90,
        inactive_opacity = 0.80,

        dim_inactive = true,
        dim_strength = 0.04,

        shadow = {
            enabled        = true,
            range          = 32,
            render_power   = 4,
            offset         = { 0, 10 },
            color          = "rgba(05030cd9)",
            color_inactive = "rgba(05030c80)",
        },

        blur = {
            enabled           = true,
            size              = 10,
            passes            = 4,
            new_optimizations = true,
            ignore_opacity    = true,
            xray              = false,
            noise             = 0.02,
            contrast          = 1.1,
            brightness        = 0.9,
            vibrancy          = 0.35,
            vibrancy_darkness = 0.3,
            popups            = true,
        },
    },
})
