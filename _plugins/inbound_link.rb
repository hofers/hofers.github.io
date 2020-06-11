module Jekyll
  class InboundLinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      # Split the input variable (omitting error checking)
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
end

Liquid::Template.register_tag('inbound_link', Jekyll::InboundLinkTag)