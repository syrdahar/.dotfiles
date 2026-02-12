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
