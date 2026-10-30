-- ──────────────────────────────────────────────────────────────
--  helpers.lua — outils partagés par les fichiers de la config Lua
--
--  bindd(touches, "Catégorie · description", action, options)
--    action = commande shell (chaîne → hl.dsp.exec_cmd), dispatcher hl.dsp.*,
--             fonction Lua, ou enter_submap("nom")
--  bind(touches, action, options)       même chose, sans description (masqué
--                                       de l'aide, de la palette et de la cheatsheet)
--  submap("nom", function() … end)      binds d'un submap
--
--  Depuis Hyprland 0.57, `hyprctl binds` n'affiche plus la commande d'un bind
--  (dispatcher = « HL.Dispatcher(…) », arg = numéro interne). Les binds décrits
--  sont donc aussi rangés dans un registre, lu par les scripts desk / keybinds.sh :
--    hyprctl repl 'desk_binds()'                       → JSON [{description, submap, dispatcher, arg}]
--    hyprctl eval 'desk_run([==[description]==], [==[submap]==])'  → exécute ce bind
-- ──────────────────────────────────────────────────────────────

local M = {}

M.registry = {}
local current_submap = ""

-- Marqueur : bind qui ouvre un submap (retrouvé par la cheatsheet : « touche d'entrée → touche »)
function M.enter_submap(name)
    return { __submap = name }
end

local function resolve(action)
    if type(action) == "string" then
        return hl.dsp.exec_cmd(action), "exec", action
    elseif type(action) == "table" and action.__submap then
        return hl.dsp.submap(action.__submap), "submap", action.__submap
    elseif type(action) == "function" then
        return action, "lua", ""
    end
    return action, tostring(action), ""
end

function M.bindd(keys, desc, action, opts)
    opts = opts or {}
    local o = { description = desc }
    for k, v in pairs(opts) do o[k] = v end
    local a, dispatcher, arg = resolve(action)
    if opts.mouse then dispatcher = "mouse" end
    hl.bind(keys, a, o)
    M.registry[#M.registry + 1] = {
        desc = desc, submap = current_submap, dispatcher = dispatcher, arg = arg, action = a,
    }
end

function M.bind(keys, action, opts)
    local a = resolve(action)
    hl.bind(keys, a, opts)
end

function M.submap(name, fn)
    hl.define_submap(name, function()
        local prev = current_submap
        current_submap = name
        fn()
        current_submap = prev
    end)
end

-- ── Accès depuis hyprctl (scripts) ───────────────────────────
local ESC = { ['"'] = '\\"', ["\\"] = "\\\\", ["\n"] = "\\n", ["\r"] = "\\r", ["\t"] = "\\t" }
local function json_str(s)
    return '"' .. (tostring(s):gsub('[%c"\\]', function(c)
        return ESC[c] or string.format("\\u%04x", c:byte())
    end)) .. '"'
end

function desk_binds()
    local out = {}
    for _, b in ipairs(M.registry) do
        out[#out + 1] = string.format('{"description":%s,"submap":%s,"dispatcher":%s,"arg":%s}',
            json_str(b.desc), json_str(b.submap), json_str(b.dispatcher), json_str(b.arg))
    end
    return "[" .. table.concat(out, ",") .. "]"
end

-- desk_run(description [, submap]) : sans submap, préfère le bind global
function desk_run(desc, submap)
    local found
    for _, b in ipairs(M.registry) do
        if b.desc == desc then
            if submap ~= nil and submap ~= "" then
                if b.submap == submap then found = b break end
            elseif b.submap == "" then
                found = b break
            elseif not found then
                found = b
            end
        end
    end
    if not found then error("bind introuvable : " .. desc) end
    if found.dispatcher == "mouse" then error("bind souris : à faire avec la souris") end
    if type(found.action) == "function" then
        found.action()
    else
        hl.dispatch(found.action)
    end
    return "ok"
end

-- desk_fit(fenêtre, l, h [, x, y]) : taille (et position) en fraction de l'écran courant,
-- ex « resizeactive exact 70% 65% » / « moveactive exact 66% 62% ». Sans x/y : centrée.
function desk_fit(window, w, h, x, y)
    local m = hl.get_active_monitor()
    if not m then return "no monitor" end
    local mw, mh = m.width / m.scale, m.height / m.scale
    hl.dispatch(hl.dsp.window.resize({ window = window, x = math.floor(mw * w), y = math.floor(mh * h) }))
    if x and y then
        hl.dispatch(hl.dsp.window.move({ window = window, x = m.x + math.floor(mw * x), y = m.y + math.floor(mh * y) }))
    else
        hl.dispatch(hl.dsp.window.center({ window = window }))
    end
    return "ok"
end

return M
