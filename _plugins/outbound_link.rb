module Jekyll
  class OutboundLinkTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      # Split the input variable (omitting error checking)
      input_split = split_params(@input)
      link = input_split[0].strip
      text = input_split[1].strip
  
      # Write the output HTML string
      output =  "<a href=\"#{link}\" target=\"_blank\" rel=\"noreferrer\">#{text}</a>"
  
      # Render it on the page by returning it
      return output;
    end
  
    def split_params(params)
      params.split("|")
    end
  end
end

Liquid::Template.register_tag('outbound_link', Jekyll::OutboundLinkTag)