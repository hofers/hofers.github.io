module Jekyll
  class EmailTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      # Split the input variable (omitting error checking)
      email = context[@input.strip]
  
      # Write the output HTML string
      output =  "<a href=\"mailto:#{email}\" target=\"_blank\" rel=\"noreferrer\">#{email}</a>"
  
      # Render it on the page by returning it
      return output;
    end
  end
end

Liquid::Template.register_tag('email', Jekyll::EmailTag)