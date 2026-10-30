-- ──────────────────────────────────────────────────────────────
--  Multi-écran (2026-10-09) — chargé en dernier depuis hyprland.lua.
--  Les règles nommées priment sur la règle générique
--  hl.monitor({ output = "" … }) de hyprland.lua, qui reste
--  le repli pour tout autre écran branché.
--  (monitors.conf = ancien fichier nwg-displays, non chargé.)
-- ──────────────────────────────────────────────────────────────

-- Portable : origine 0x0, échelle 1.5
hl.monitor({ output = "eDP-1", mode = "1920x1200@60", position = "0x0", scale = 1.5 })

-- MSI MP2412 : à gauche du portable, 100 Hz (le mode « preferred » choisissait 60 Hz).
-- Repéré par sa description pour suivre l'écran quel que soit le port (HDMI, dock USB-C…).
hl.monitor({ output = "desc:Microstep MSI MP2412 BA9H595304773", mode = "1920x1080@100", position = "-1920x0", scale = 1 })
