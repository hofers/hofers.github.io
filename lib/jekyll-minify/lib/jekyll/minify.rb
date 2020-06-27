require "jekyll/minify/version"

require 'jekyll'
require 'rubygems'
require 'uglifier'

module Jekyll
  module Minify
    class Error < StandardError; end
    class MinifyJS < Jekyll::Command
      def self.init_with_program(prog)
        prog.command(:minify) do |c|
          c.syntax "minify"
          c.description 'Minifies JS files in `_includes/scripts` folder.'
  
          c.action do |args, options|
            Dir.foreach(Dir.pwd + '/_includes/scripts') do |file|
              next if file == '.' or file == '..' or file.include? '.min'
              filepath = Dir.pwd + '/_includes/scripts/' + file
              output = Uglifier.compile(File.open(filepath, 'r'), harmony: true)
              File.open(filepath, 'w').write(output)
            end
          end
        end
      end
    end
  end
end
