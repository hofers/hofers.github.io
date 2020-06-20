require 'jekyll-replace-last'
require 'yaml'

module Jekyll
  # {% my_email %}
  # creates a mailto: link to the address specified at `site.email` in `_config.yml`
  class EmailTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @email = ""
      config_path = "./_config.yml"
      if File.exist?("../_config.yml")
        config_path = "../_config.yml"
      end
      File.foreach(config_path) { |line| if line[0..4] == "email" then @email = line[7..-2] end }
    end
  
    def render(context)
      return "<a href=\"mailto:#{@email}\" target=\"_blank\" rel=\"noreferrer\">#{@email}</a>"
    end
  end

  # {% download %}
  # appends download attribute
  class DownloadTag < Liquid::Tag
    def render(context)
      return "{:download=''}"
    end
  end

  # {% out %}
  # appends outbound link attributes
  class OutboundTag < Liquid::Tag
    def render(context)
      return "{:target='_blank' rel='noreferrer'}"
    end
  end

  # {% pdf TITLE | FILE %}
  # creates an iframe with title `TITLE` for displaying a PDF located at `FILE`
  # uses PDF.js for rendering PDFs
  class PDFTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      input_split = @input.split("|")
      file = context[input_split[0].strip] || input_split[0].strip
      if input_split.size == 1
        title = file
      else
        title = context[input_split[1].strip] || input_split[1].strip
      end

      return "<iframe title=\"#{title}\" src=\"/lib/pdf.js/web/viewer.html?file=#{file}\"></iframe>"
    end
  end

  # {% CONTENT | kill_runts %}
  # replaces the last space in `CONTENT` with a non-breaking space
  # used to prevent runts in text
  module KillRuntsFilter
    def kill_runts(input)
      "#{replace_last(input, " ", "&nbsp;")}"
    end
  end
end

Liquid::Template.register_tag('my_email', Jekyll::EmailTag)
Liquid::Template.register_tag('download', Jekyll::DownloadTag)
Liquid::Template.register_tag('out', Jekyll::OutboundTag)
Liquid::Template.register_tag('pdf', Jekyll::PDFTag)
Liquid::Template.register_filter(Jekyll::KillRuntsFilter)