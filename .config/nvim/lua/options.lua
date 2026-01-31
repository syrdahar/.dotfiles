require "nvchad.options"

local o = vim.opt

-------------------------------------- options ------------------------------------------
o.backup = false
o.swapfile = false
o.undofile = true
o.writebackup = false

o.clipboard = "unnamedplus"
o.mouse = "a"

o.cmdheight = 2
o.completeopt = { "menuone", "noselect" }
o.conceallevel = 0
o.fileencoding = "utf-8"

o.hlsearch = true
o.incsearch = true
o.ignorecase = true

o.ro = false

o.pumheight = 10

o.expandtab = true
o.smartcase = true
o.smartindent = true
o.splitbelow = true
o.splitright = true

o.termguicolors = true
o.timeoutlen = 1000
o.updatetime = 300

o.shiftwidth = 4
o.tabstop = 4
o.softtabstop = 4

o.cursorline = false
o.number = true
o.relativenumber = true
o.numberwidth = 4
o.wrap = false

o.scrolloff = 8
o.sidescrolloff = 8

-- Create an autocommand group for file-specific settings
vim.api.nvim_create_augroup("FileTypeSpecific", { clear = true })

-- Set shiftwidth and tabstop to 2 for HTML, CSS, JavaScript, and Lua files
vim.api.nvim_create_autocmd("FileType", {
    pattern = { "html", "css", "javascript", "lua" },
    callback = function()
        vim.opt_local.shiftwidth = 2
        vim.opt_local.tabstop = 2
    end,
    group = "FileTypeSpecific",
})

vim.cmd("autocmd BufEnter * set formatoptions-=cro")
vim.cmd("autocmd BufEnter * setlocal formatoptions-=cro")

vim.opt.shortmess:append "c"
