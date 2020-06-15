# [seanhofer.com](https://seanhofer.com)

![seanhofer.com](/assets/images/mysite.jpg)

This is the repo for my personal professional site, available at https://seanhofer.com. It's hosted on GitHub Pages, but built and deployed via a custom GitHub Action that allows me to include custom plugins disallowed by GitHub Pages. My DNS services are handled by Cloudflare and my domain is from Google Domains.

It's made with Jekyll and Sass, and it uses [jekyll-replace-last](https://github.com/hofers/jekyll-replace-last), a simple Jekyll plugin I made to mimic Liquid's `replace-first` filter for the last occurrence of a substring within a string. I use this to automatically prevent [runts](https://indesignsecrets.com/3-ways-to-fix-runts-in-your-text.php) in some text tags by replacing the final space with a non-breaking space.

My Jekyll source code can be found on the [`jekyll`](https://github.com/hofers/hofers.github.io/tree/jekyll) branch, and my compiled static site can be found on the [`master`](https://github.com/hofers/hofers.github.io/tree/master) branch.