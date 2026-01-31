require "nvchad.mappings"

local opts = { noremap = true, silent = true }
local term_opts = { silent = true }

local map = vim.keymap.set

map("n", ";", ":", { desc = "CMD enter command mode" })

-- Plugin specific
map('n', '<leader>ca', '<cmd>lua vim.lsp.buf.code_action()<cr>', opts)

-- map({ "n", "i", "v" }, "<C-s>", "<cmd> w <cr>")

-- Modes
--   normal_mode = "n",
--   insert_mode = "i",
--   visual_mode = "v",
--   visual_block_mode = "x",
--   term_mode = "t",
--   command_mode = "c",

-- Normal --
-- Better window navigation
map("n", "<C-h>", "<C-w>h", opts)
map("n", "<C-j>", "<C-w>j", opts)
map("n", "<C-k>", "<C-w>k", opts)
map("n", "<C-l>", "<C-w>l", opts)

map("n", "<C-S-h>", "<C-w><S-h>", opts)
map("n", "<C-S-j>", "<C-w><S-j>", opts)
map("n", "<C-S-k>", "<C-w><S-k>", opts)
map("n", "<C-S-l>", "<C-w><S-l>", opts)

map("n", "<C-d>", "<C-d>zz", opts)
map("n", "<C-u>", "<C-u>zz", opts)

--keymap("n", "<leader>e", ":Lex 30<cr>", opts)

-- Resize with arrows
map("n", "<C-Up>", ":resize +1<CR>", opts)
map("n", "<C-Down>", ":resize -1<CR>", opts)
map("n", "<C-Left>", ":vertical resize -1<CR>", opts)
map("n", "<C-Right>", ":vertical resize +1<CR>", opts)

-- Navigate buffers
map("n", "<S-l>", ":bnext<CR>", opts)
map("n", "<S-h>", ":bprevious<CR>", opts)

-- Insert --
-- Press jk fast to enter
-- keymap("i", "jk", "<ESC>", opts)

-- Visual --
-- Stay in indent mode
-- keymap("v", "<", "<gv", opts)
-- keymap("v", ">", ">gv", opts)

map("n", "Q", "<nop>", opts)

-- Move text up and down
map("v", "<A-j>", ":m .+1<CR>==", opts)
map("v", "<A-k>", ":m .-2<CR>==", opts)
map("v", "p", '"_dP', opts)

-- Visual Block --
-- Move text up and down
map("x", "J", ":move '>+1<CR>gv=gv", opts)
map("x", "K", ":move '<-2<CR>gv=gv", opts)
map("x", "<A-j>", ":move '>+1<CR>gv=gv", opts)
map("x", "<A-k>", ":move '<-2<CR>gv=gv", opts)
map("x", "p", '"_dP', opts)

-- Terminal --
-- Better terminal navigation
map("t", "<C-h>", "<C-\\><C-N><C-w>h", term_opts)
map("t", "<C-j>", "<C-\\><C-N><C-w>j", term_opts)
map("t", "<C-k>", "<C-\\><C-N><C-w>k", term_opts)
map("t", "<C-l>", "<C-\\><C-N><C-w>l", term_opts)
