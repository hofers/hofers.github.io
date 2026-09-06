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
  # e.g. `:wave:` -> 👋.
  module UnicodeEmoji
    SKIP_TAGS = %w[code pre tt script style].freeze

    def self.emojiable?(doc)
      return false unless doc.is_a?(Jekyll::Page) || doc.write?
      doc.output_ext == ".html" || doc.permalink.to_s.end_with?("/")
    end

    # substitutes in text nodes only, so tag attributes and SKIP_TAGS contents are untouched
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
  #
  # `CONTENT` is rendered HTML, so the last space is looked for outside tags: replacing
  # one inside a tag silently breaks the attribute it sits in.
  module KillRuntsFilter
    def kill_runts(input)
      text = input.to_s
      cut = last_text_space(text)
      return text if cut.nil?

      "#{text[0...cut]}&nbsp;#{text[(cut + 1)..]}"
    end

    def last_text_space(text)
      depth = 0
      found = nil

      text.each_char.with_index do |char, index|
        case char
        when "<" then depth += 1
        when ">" then depth -= 1 if depth.positive?
        when " " then found = index if depth.zero?
        end
      end

      found
    end
  end

  # {{ CONTENT | aberrate }}                   always separated
  # {{ CONTENT | aberrate: "hover" }}          separates on hover/focus; inside a link,
  #                                            follows that link's hover
  # {{ CONTENT | aberrate: "wander" }}         separation animates continuously, to about
  #                                            +/- the authored distance on both axes
  # {{ CONTENT | aberrate: "hover wander" }}   the walk, but only while hovered
  # {{ CONTENT | aberrate: "lift" }}           summed past white on an HDR display
  # {{ CONTENT | aberrate: "0.05em" }}         a wider separation than the default
  # {{ CONTENT | aberrate: "hover 0.05em" }}   options are space-separated, in any order
  #
  # wraps CONTENT in the markup the `.aberrate` styles need: the class, and a
  # `data-text` copy of the string that the two pseudo-element layers draw via
  # `content: attr(data-text)`. See docs/chromatic-aberration.md.
  #
  # The filter writes only the wrapper; `data-text` is filled in by the post_render hook
  # at the bottom of this file, because Liquid runs before kramdown's smart quotes and
  # the emoji substitution and all three layers must draw the same string.
  module Aberration
    # Interpolated into a style attribute, so anything but a length is dropped rather
    # than trusted.
    SHIFT = /\A-?(?:\d+\.?\d*|\.\d+)(?:em|rem|px|ch|%)\z/

    # An `&` that does not already open an entity: entities must reach `attr()` intact,
    # so `&nbsp;` from kill_runts stays a real space.
    BARE_AMPERSAND = /&(?!(?:[a-zA-Z][a-zA-Z0-9]*|\#[0-9]+|\#x[0-9a-fA-F]+);)/

    def self.wrap(input, options = nil)
      text = input.to_s.strip
      return text if text.empty?

      classes, shift = parse(options)
      %(<span class="#{classes}"#{style(shift)}>#{text}</span>)
    end

    VARIANTS = %w[hover wander lift].freeze

    def self.parse(options)
      variants = []
      shift = nil

      options.to_s.split(/\s+/).reject(&:empty?).each do |token|
        case token
        when *VARIANTS then variants |= [token]
        when SHIFT     then shift = token
        else
          Jekyll.logger.warn "Aberrate:", "ignoring option #{token.inspect}; expected " \
            "#{VARIANTS.map(&:inspect).join(", ")} or a CSS length"
        end
      end

      # Emitted in VARIANTS order rather than the order they were written, so the same
      # pair of options is the same string in the output whichever way it was asked for.
      classes = ["aberrate"] + VARIANTS.select { |v| variants.include?(v) }
                                       .map { |variant| "aberrate--#{variant}" }

      [classes.join(" "), shift]
    end

    def self.style(shift)
      return "" if shift.nil?

      %( style="--ca-shift:#{shift}")
    end

    def self.attribute(text)
      text.gsub(BARE_AMPERSAND, "&amp;").gsub('"', "&quot;").gsub("<", "&lt;").gsub(">", "&gt;")
    end

    OPENING = /<span[\s]+class="[^"]*\baberrate\b[^"]*"[^>]*>/
    ANY_SPAN = %r{</?span\b[^>]*>}

    # Fills in data-text on every wrapper the filter left, read off the rendered HTML.
    def self.populate(html)
      return html unless html.include?("aberrate")

      scanner = StringScanner.new(html)
      out = +""

      while (consumed = scanner.scan_until(OPENING))
        tag = scanner.matched
        out << consumed[0...-tag.length]

        inner = read_span(scanner)
        plain = inner.gsub(%r{</?[^>]+>}, "")

        if plain != inner
          Jekyll.logger.warn "Aberrate:", "markup inside #{inner.inspect} is not " \
            "mirrored onto the color layers; wrap the tag rather than the text inside it"
        end

        out << tag.sub(/\/?>\z/, %( data-text="#{attribute(plain)}">)) << inner << "</span>"
      end

      out << scanner.rest
      out
    end

    # Everything up to this span's own closing tag, counting nested spans.
    def self.read_span(scanner)
      depth = 1
      inner = +""

      while (consumed = scanner.scan_until(ANY_SPAN))
        tag = scanner.matched
        body = consumed[0...-tag.length]

        if tag.start_with?("</")
          depth -= 1
          return inner << body if depth.zero?
        else
          depth += 1
        end

        inner << body << tag
      end

      inner << scanner.rest
      scanner.terminate
      inner
    end
  end

  module AberrateFilter
    def aberrate(input, shift = nil)
      Aberration.wrap(input, shift)
    end
  end
end

Liquid::Template.register_tag('my_email', Jekyll::EmailTag)
Liquid::Template.register_tag('download', Jekyll::DownloadTag)
Liquid::Template.register_tag('out', Jekyll::OutboundTag)
Liquid::Template.register_tag('pdf', Jekyll::PDFTag)
Liquid::Template.register_filter(Jekyll::KillRuntsFilter)
Liquid::Template.register_filter(Jekyll::EncodeEmailFilter)
Liquid::Template.register_filter(Jekyll::AberrateFilter)

Jekyll::Hooks.register [:pages, :documents], :post_render do |doc|
  next unless Jekyll::UnicodeEmoji.emojiable?(doc)
  doc.output = Jekyll::UnicodeEmoji.emojify(doc.output)
end

# Registered after the emoji hook, so a shortcode inside an aberrated span reaches the
# color layers as the character it renders as.
Jekyll::Hooks.register [:pages, :documents], :post_render do |doc|
  doc.output = Jekyll::Aberration.populate(doc.output)
end
