return {
  {
    "stevearc/conform.nvim",
    -- event = 'BufWritePre', -- uncomment for format on save
    opts = require "configs.conform",
  },

  -- These are some examples, uncomment them if you want to see them work!
  {
    "neovim/nvim-lspconfig",
    config = function()
      require "configs.lspconfig"
    end,
  },

  {
    "nvim-telescope/telescope.nvim",
    opts = {
      defaults = {
        file_ignore_patterns = {
          "node_modules",
          "%.git",
          "%.cache",
          "target",
          "build",
        },
      },
    },
  },

-- {
--     "neovim/nvim-lspconfig",
--     config = function()
--       require("nvchad.configs.lspconfig").defaults()
--       local lspconfig = require "lspconfig"
-- 
--       -- Tinymist Setup
--       lspconfig.tinymist.setup {
--         offset_encoding = "utf-8",
--         settings = {
--             exportPdf = "onType", -- Export PDF on type
--             outputPath = "$root/target/$dir/$name", -- Optional: keep build artifacts organized
--             formatterMode = "typstyle", -- Use 'typstyle' for formatting
--         }
--       }
--     end,
--   },

  {
    "chomosuke/typst-preview.nvim",
    ft = "typst",
    version = "1.*",
    build = function() require("typst-preview").update() end,
  },

  {
    "benlubas/molten-nvim",
    version = "^1.0.0",
    dependencies = { "3rd/image.nvim" },
    build = ":UpdateRemotePlugins",
    init = function()
      vim.g.molten_image_provider = "image.nvim"
      vim.g.molten_output_win_max_height = 20
      vim.g.molten_auto_open_output = false
      vim.g.molten_wrap_output = true
      vim.g.molten_virt_text_output = true
    end,
    cmd = { "MoltenInit", "MoltenDeinit", "MoltenRestart", "MoltenLoad" }, -- Expose les commandes au lazy-loader
    keys = {
      { "<leader>mi", ":MoltenInit<CR>", desc = "Initialize Kernel" },
      { "<leader>e", ":MoltenEvaluateOperator<CR>", desc = "Evaluate Operator" },
      { "<leader>rl", ":MoltenEvaluateLine<CR>", desc = "Evaluate Line" },
      { "<leader>rr", ":MoltenReevaluateCell<CR>", desc = "Re-evaluate Cell" },
      { "<leader>r", ":<C-u>MoltenEvaluateVisual<CR>", mode = "v", desc = "Evaluate Selection" },
      { "<leader>rd", ":MoltenDelete<CR>", desc = "Delete Cell Output" },
      { "<leader>oh", ":MoltenHideOutput<CR>", desc = "Hide Output Window" },
      { "<leader>os", ":MoltenShowOutput<CR>", desc = "Show Output Window" },
    },
  },

  {
    "GCBallesteros/jupytext.nvim",
    config = function()
      require("jupytext").setup({
        style = "percent",
        output_extension = "py",
        force_ft = "python",
      })
    end,
  },

  {
    "3rd/image.nvim",
    opts = {
      -- Le backend dépend strictement de ton émulateur de terminal.
      -- Valeurs communes : "kitty", "ueberzug" (pour tmux/x11), ou "ghostty".
      backend = "ueberzug",
      max_width = 100,
      max_height = 12,
      max_height_window_percentage = math.huge,
      max_width_window_percentage = math.huge,
      window_overlap_clear_enabled = true,
      window_overlap_clear_ft_ignore = { "cmp_menu", "cmp_docs", "" },
    }
  },

  -- test new blink
  -- { import = "nvchad.blink.lazyspec" },

  -- {
  -- 	"nvim-treesitter/nvim-treesitter",
  -- 	opts = {
  -- 		ensure_installed = {
  -- 			"vim", "lua", "vimdoc",
  --      "html", "css"
  -- 		},
  -- 	},
  -- },
}
