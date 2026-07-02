require 'sketchup.rb'
require 'extensions.rb'
require 'json'
require 'socket'

module SU_MCP
  unless file_loaded?(__FILE__)
    ex = SketchupExtension.new('SketchUp MCP (NeoNexAI)', 'su_mcp/main')
    ex.description = 'MCP server for SketchUp — NeoNexAI hardened fork (curated tools, no arbitrary code execution)'
    ex.version     = '1.0.0'
    ex.copyright   = '2026'
    Sketchup.register_extension(ex, true)
    file_loaded(__FILE__)
  end
end 