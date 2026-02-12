require("nvchad.configs.lspconfig").defaults()

local servers = { "html", "cssls", "clangd", "tinymist" }
vim.lsp.enable(servers)

local typst_config = {
       offset_encoding = "utf-8",
       settings = {
           exportPdf = "onType", -- Export PDF on type
           outputPath = "$root/target/$dir/$name", -- Optional: keep build artifacts organized
           formatterMode = "typstyle", -- Use 'typstyle' for formatting
       }
    }

vim.lsp.config("tinymist", { settings = typst_config } )
-- read :h vim.lsp.config for changing options of lsp servers 
