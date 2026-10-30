-- ──────────────────────────────────────────────────────────────
--  Programmes utilisés par les raccourcis (ex-$terminal, $menu… de hyprland.conf)
-- ──────────────────────────────────────────────────────────────

return {
    terminal    = "alacritty",
    lockscreen  = "pidof hyprlock || hyprlock",
    fileManager = "dolphin",
    browser     = "librewolf",
    menu        = "rofi -show drun",
    powermenu   = "~/.config/waybar/scripts/powermenu.sh",
    clipboard   = 'cliphist list | rofi -dmenu -p "󰅌  clipboard" -display-columns 2 | cliphist decode | wl-copy',
}
