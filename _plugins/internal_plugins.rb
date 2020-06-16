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
      output =  "<a href=\"mailto:#{@email}\" target=\"_blank\" rel=\"noreferrer\">#{@email}</a>"
      return output;
    end
  end

  # {% link URL | TEXT %}
  # creates a link tag for URLs directed to `URL` with `TEXT` as the link text
  # automatically formats outbound links with `target="_blank"` and `rel="noreferrer"`
  class LinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      input_split = split_params(@input)
      link = input_split[0].strip
      text = input_split[1].strip

      if input_split[2] && input_split[2].strip == "download"
        output =  "<a href=\"#{context[link]}\" download>#{text}</a>"
      elsif link[0] == "/" || link[0] == "#"
        output =  "<a href=\"#{link}\">#{text}</a>"
      else 
        output =  "<a href=\"#{link}\" target=\"_blank\" rel=\"noreferrer\">#{text}</a>"
      end
  
      return output;
    end
  
    def split_params(params)
      params.split("|")
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
Liquid::Template.register_filter(Jekyll::KillRuntsFilter)