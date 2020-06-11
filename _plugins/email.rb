module Jekyll
  class EmailTag < Liquid::Tag
    def initialize(tag_name, input, tokens)
      super
      @input = input
    end
  
    def render(context)
      email = context[@input.strip]
  
      output =  "<a href=\"mailto:#{email}\" target=\"_blank\" rel=\"noreferrer\">#{email}</a>"
  
      return output;
    end
  end
end

Liquid::Template.register_tag('email', Jekyll::EmailTag)