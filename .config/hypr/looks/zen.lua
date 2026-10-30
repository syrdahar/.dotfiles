-- ──────────────────────────────────────────────────────────────
--  Look "zen" : bordures quasi invisibles, fenêtres inactives atténuées, coins doux, blur et ombre douce
--  Activé via ~/.config/hypr/look.lua → looks/zen.lua (rice.sh look zen)
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/zen.lua
-- ──────────────────────────────────────────────────────────────

hl.config({
    general = {
        col = {
            active_border   = "rgba(e6ddf022)",
            inactive_border = "rgba(00000000)",
        },
    },

    decoration = {
        rounding       = 18,
        rounding_power = 3,

        active_opacity   = 1.0,
        inactive_opacity = 0.90,

        dim_inactive = true,
        dim_strength = 0.25,

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
