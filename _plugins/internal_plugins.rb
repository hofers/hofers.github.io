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
  #
  # The last space is looked for in text only. `CONTENT` here is rendered HTML, and a
  # plain replace_last lands inside the final tag whenever a paragraph ends in markup --
  # `<a href=` becomes `<a&nbsp;href=`, and an attribute is silently lost. A space inside
  # a tag is never the runt anyway; the one that matters is between the last two words.
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
  # {{ CONTENT | aberrate: "0.05em" }}         a wider separation than the default
  # {{ CONTENT | aberrate: "hover 0.05em" }}   options are space-separated, in any order
  #
  # wraps CONTENT in the markup the `.aberrate` styles need: the class, and a
  # `data-text` copy of the string that the two pseudo-element layers draw via
  # `content: attr(data-text)`. See _includes/styles/_sass/_aberration.scss. The layers
  # are derived from the wrapped text's own color, so this can go anywhere without
  # having to say what color it lands on.
  #
  # The filter only writes the wrapper; `data-text` is filled in afterwards by the
  # post_render hook at the bottom of this file. It has to be, because the three layers
  # draw the same string three times and any difference between them misregisters every
  # glyph after it -- and Liquid runs before two things that still change the text:
  # kramdown's smart quotes (`"hi"` -> `“hi”`, and every apostrophe), and the emoji
  # substitution above. Reading the attribute off the *rendered* HTML is the only point
  # at which what the layers draw is guaranteed to be what the element says.
  module Aberration
    # Only lengths, and only into the one custom property -- this is interpolated
    # into a style attribute, so anything else is dropped rather than trusted.
    SHIFT = /\A-?(?:\d+\.?\d*|\.\d+)(?:em|rem|px|ch|%)\z/

    # An `&` that does not already open an entity. Entities are left intact: a
    # data-text attribute decodes them exactly as the element's own text does, so
    # `&nbsp;` from kill_runts survives into content: attr() as a real space.
    BARE_AMPERSAND = /&(?!(?:[a-zA-Z][a-zA-Z0-9]*|\#[0-9]+|\#x[0-9a-fA-F]+);)/

    def self.wrap(input, options = nil)
      text = input.to_s.strip
      return text if text.empty?

      classes, shift = parse(options)
      %(<span class="#{classes}"#{style(shift)}>#{text}</span>)
    end

    # Space-separated options in any order: any of the variants, and/or a CSS length.
    # They compose -- each one supplies a different factor of the displacement, so
    # "hover wander" is a walk that runs only while hovered.
    VARIANTS = %w[hover wander].freeze

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

    # --ca-shift is the authored separation in every variant: the distance the layers
    # hold, the distance the hover gate opens to, and the amplitude the wander walks.
    # The variants each scale it by a factor of their own rather than overwriting it, so
    # an inline value here does not have to fight a rest state for specificity.
    def self.style(shift)
      return "" if shift.nil?

      %( style="--ca-shift:#{shift}")
    end

    def self.attribute(text)
      text.gsub(BARE_AMPERSAND, "&amp;").gsub('"', "&quot;").gsub("<", "&lt;").gsub(">", "&gt;")
    end

    # Fills in data-text on every wrapper the filter left, reading it off the rendered
    # HTML. Runs last, so smart quotes and emoji are already applied.
    OPENING = /<span[\s]+class="[^"]*\baberrate\b[^"]*"[^>]*>/
    ANY_SPAN = %r{</?span\b[^>]*>}

    def self.populate(html)
      return html unless html.include?("aberrate")

      scanner = StringScanner.new(html)
      out = +""

      while (consumed = scanner.scan_until(OPENING))
        tag = scanner.matched
        out << consumed[0...-tag.length]

        inner = read_span(scanner)
        plain = inner.gsub(%r{</?[^>]+>}, "")

        # The layers can only draw a string, so tags inside cannot be mirrored onto
        # them. Strip them for the attribute and say so, rather than letting three
        # disagreeing layers ship: that misregisters every glyph after the tag, and is
        # a miserable thing to diagnose from the rendered page.
        if plain != inner
          Jekyll.logger.warn "Aberrate:", "markup inside #{inner.inspect} is not " \
            "mirrored onto the color layers; wrap the tag rather than the text inside it"
        end

        out << tag.sub(/\/?>\z/, %( data-text="#{attribute(plain)}">)) << inner << "</span>"
      end

      out << scanner.rest
      out
    end

    # Everything up to this span's own closing tag, counting nested spans so that a
    # wrapper around content that itself contains one is not cut short.
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

# after the emoji hook, so a shortcode inside an aberrated span reaches the color
# layers as the character it renders as rather than as `:wave:`
Jekyll::Hooks.register [:pages, :documents], :post_render do |doc|
  doc.output = Jekyll::Aberration.populate(doc.output)
end
