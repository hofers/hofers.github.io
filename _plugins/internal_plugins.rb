require 'jekyll-replace-last'
require 'yaml'
require 'strscan'
require 'gemoji'

module Jekyll
  # {% CONTENT | encode %}
  # encodes a given email for Cloudflare's email obfuscator
  module EncodeEmailFilter
    def encode(email)
      key = 20.to_s(16)
      hex_key = key.hex
      result = hex_key.to_s(16)
      email.split('').each do |n|
        char = n.to_s().sum.to_i()
        result += (char ^ hex_key).to_s(16)
      end
      return result
    end
  end

  # {% my_email %}
  # creates a mailto: link to the address specified at `site.email` in `_config.yml`
  class EmailTag < Liquid::Tag
    include EncodeEmailFilter
    def initialize(tag_name, input, tokens)
      super
      @encoded_email = encode(Jekyll.configuration()["email"])
      unless input.nil? || input == ""
        @text = input.strip
      end
    end
  
    def render(context)
      unless @text.nil?
        @text = context[@text] || @text
      end
      return "<a href=\"/cdn-cgi/l/email-protection\##{@encoded_email}\" target=\"_blank\" rel=\"noreferrer\">" + (@text.nil? ? "<span class=\"__cf_email__\" data-cfemail=\"#{@encoded_email}\">[email&#160;protected]</span></a>" : "#{@text}</a>")
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

  # replaces every `:shortcode:` in rendered HTML with the Unicode emoji it names,
  # e.g. `:wave:` -> 👋. Stands in for jemoji, which substituted a 20px PNG served
  # from github.githubassets.com -- same authoring syntax, no request, no image.
  module UnicodeEmoji
    # tags whose contents are markup or code samples, and must be left alone
    SKIP_TAGS = %w[code pre tt script style].freeze

    # mirrors jemoji: only pages/documents that are written out as HTML
    def self.emojiable?(doc)
      return false unless doc.is_a?(Jekyll::Page) || doc.write?
      doc.output_ext == ".html" || doc.permalink.to_s.end_with?("/")
    end

    # walks the rendered HTML, substituting in text nodes only, so that neither
    # tag attributes nor the contents of SKIP_TAGS are touched
    def self.emojify(html)
      return html unless html.include?(":")

      scanner = StringScanner.new(html)
      out = +""
      skipping = nil

      until scanner.eos?
        if (tag = scanner.scan(/<[^>]*>/m))
          out << tag
          if skipping
            skipping = nil if tag.downcase.start_with?("</#{skipping}")
          elsif (name = tag[/\A<([a-zA-Z0-9]+)/, 1]&.downcase)
            skipping = name if SKIP_TAGS.include?(name) && !tag.end_with?("/>")
          end
        else
          text = scanner.scan(/[^<]+/m) || scanner.getch
          out << (skipping ? text : substitute(text))
        end
      end

      out
    end

    def self.substitute(text)
      text.gsub(shortcode_pattern) do
        ::Emoji.find_by_alias(Regexp.last_match(1)).raw
      end
    end

    # matches known aliases only, longest first, so that neither an unrecognised
    # shortcode nor incidental colons (`3:4:5`, `a:hover`) are ever rewritten
    def self.shortcode_pattern
      @shortcode_pattern ||= begin
        aliases = ::Emoji.all.flat_map(&:aliases)
                          .sort_by { |name| -name.length }
                          .map { |name| Regexp.escape(name) }
        Regexp.new(":(#{aliases.join("|")}):")
      end
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
Liquid::Template.register_filter(Jekyll::EncodeEmailFilter)

Jekyll::Hooks.register [:pages, :documents], :post_render do |doc|
  next unless Jekyll::UnicodeEmoji.emojiable?(doc)
  doc.output = Jekyll::UnicodeEmoji.emojify(doc.output)
end
