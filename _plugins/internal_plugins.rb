require 'jekyll-replace-last'
require 'yaml'

module Jekyll
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

  class InboundLinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      input_split = split_params(@input)
      link = input_split[0].strip
      text = input_split[1].strip
  
      output =  "<a href=\"#{link}\">#{text}</a>"
  
      return output;
    end
  
    def split_params(params)
      params.split("|")
    end
  end

  class OutboundLinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      input_split = split_params(@input)
      link = input_split[0].strip
      text = input_split[1].strip
  
      output =  "<a href=\"#{link}\" target=\"_blank\" rel=\"noreferrer\">#{text}</a>"
  
      return output;
    end
  
    def split_params(params)
      params.split("|")
    end
  end

  module KillRuntsFilter
    def kill_runts(input)
      "#{replace_last(input, " ", "&nbsp;")}"
    end
  end
end

Liquid::Template.register_tag('my_email', Jekyll::EmailTag)
Liquid::Template.register_tag('inbound_link', Jekyll::InboundLinkTag)
Liquid::Template.register_tag('outbound_link', Jekyll::OutboundLinkTag)
Liquid::Template.register_filter(Jekyll::KillRuntsFilter)