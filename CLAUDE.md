# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Overview

This is a Jekyll-based personal professional website for Sean Hofer, hosted on GitHub Pages with
custom GitHub Actions deployment. The site is built with Jekyll 4.3.1 and includes custom plugins
and optimized asset processing.

## Development Commands

### Local Development
```bash
# Install dependencies
bundle install

# Start development server (serves at http://0.0.0.0:4000)
bundle exec jekyll serve
```

### Asset Processing
```bash
# Generate responsive images and WebP conversions
./bin/make-images.sh
```

## Project Structure

### Core Jekyll Architecture
- `_config.yml` - Main Jekyll configuration with custom plugins and collections
- `_layouts/` - HTML templates (default.html is the main layout)
- `_includes/` - Reusable components and assets
- `_plugins/internal_plugins.rb` - Custom Jekyll plugins and filters
- `_site/` - Generated static site output (excluded from git)

### Collections
- `_portfolio-items/` - Portfolio project entries
- `_press-items/` - Press coverage entries
- `_posts/class/` - Blog posts for class-related content

### Custom Plugins
The site uses several custom Jekyll plugins (both internal and external):
- Custom internal plugins in `_plugins/internal_plugins.rb`:
  - Email encoding filter for Cloudflare protection
  - PDF embedding with PDF.js
  - Custom Liquid tags for downloads and outbound links
  - Typography filter to prevent runts
- External plugins:
  - `jekyll-replace-last` - Replace last occurrence of strings
  - `jekyll-uglify` - JavaScript minification
  - `jekyll-make-sitemap` - Generate sitemaps
  - `jekyll-brotli` - Brotli compression
  - `jekyll-redirect-from` - URL redirects

### Asset Organization
- `_includes/styles/` - SCSS stylesheets with modular organization
- `_includes/scripts/` - JavaScript files including GA, lazy loading, contact forms
- `_includes/fonts/` - Base64 encoded font files for performance
- `assets/images/` - Optimized images with responsive variants
- `bin/` - Build scripts for image processing (WebP conversion, responsive images)

### Key Features
- Responsive image handling with automatic WebP/JPEG srcsets
- Inline critical CSS with SCSS compilation
- Custom email obfuscation for Cloudflare
- PDF.js integration for document embedding
- Lazy loading for images and assets
- Google Analytics integration
- Font Awesome icons

### Deployment
- Built and deployed via GitHub Actions (not standard GitHub Pages)
- Source code on `jekyll` branch, compiled site on `main` branch
- Custom domain with Cloudflare DNS

## Working with Content

### Adding Portfolio Items
Create markdown files in `_portfolio-items/` with frontmatter for project details.

### Adding Blog Posts
Create markdown files in `_posts/class/` following Jekyll naming conventions (YYYY-MM-DD-title.md).

### Styling
- Main styles in `_includes/styles/stylish.scss`
- Page-specific styles can be added by setting `tags: css` in frontmatter
- SCSS compilation happens inline during build

### Images
- Place source images in `assets/images/`
- Run `./bin/make-images.sh` to generate responsive variants
- Use `{% include modules/image.html image="filename" title="Alt text" %}` for optimized display