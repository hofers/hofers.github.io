source "https://rubygems.org"

gem "jekyll", "~> 4.0.0"
gem "jekyll-brotli"

group :jekyll_plugins do
  gem 'jemoji'
  gem 'jekyll-make-sitemap', "~> 1.2.0"
  gem 'jekyll-replace-last', "~> 1.0.1"
  gem "jekyll-redirect-from", "~> 0.16.0"
  gem 'jekyll-uglify', "~> 1.1.2"
end

# Windows and JRuby does not include zoneinfo files, so bundle the tzinfo-data gem
# and associated library.
install_if -> { RUBY_PLATFORM =~ %r!mingw|mswin|java! } do
  gem "tzinfo", "~> 1.2"
  gem "tzinfo-data"
end

# Performance-booster for watching directories on Windows
gem "wdm", "~> 0.1.1", :install_if => Gem.win_platform?

