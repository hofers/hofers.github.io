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

  # {% link URL | TEXT | download? %}
  # creates a link tag for URLs directed to `URL` with `TEXT` as the link text
  # automatically formats outbound links with `target="_blank"` and `rel="noreferrer"`
  # include `| download` to create a download link
  class LinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      input_split = @input.split("|")
      link = context[input_split[0].strip] || input_split[0].strip
      text = context[input_split[1].strip] || input_split[1].strip

      if input_split[2] && input_split[2].strip == "download"
        output = "<a href=\"#{link}\" download>#{text}</a>"
      elsif link[0] == "/" || link[0] == "#"
        output = "<a href=\"#{link}\">#{text}</a>"
      else 
        output = "<a href=\"#{link}\" target=\"_blank\" rel=\"noreferrer\">#{text}</a>"
      end
  
      return output;
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
      title = context[input_split[0].strip] || input_split[0].strip
      file = context[input_split[1].strip] || input_split[1].strip

      return "<iframe title=\"#{title}\" src=\"/assets/js/pdf.js/web/viewer.html?file=#{file}\"></iframe>"
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
Liquid::Template.register_tag('link', Jekyll::LinkTag)
Liquid::Template.register_tag('pdf', Jekyll::PDFTag)
Liquid::Template.register_filter(Jekyll::KillRuntsFilter)