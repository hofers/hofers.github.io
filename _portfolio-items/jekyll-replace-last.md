---
title: jekyll-replace-last
link: https://github.com/hofers/jekyll-replace-last
source: Personal Project
date: 2020-06-01
image: jekyll-replace-last
---
{%- assign highlight_text = "In typography, a «runt» occurs when the last line of a paragraph ends with:\na part of a hyphenated word\nor a single short word\nor a short lines of text with up to 10-signs at the last line of a paragraph." | split: "\n" | join: "&text=" -%}
[jekyll-replace-last](https://github.com/hofers/jekyll-replace-last){% out %} is a simple Ruby gem I made in the process of [Jekyll](https://jekyllrb.com){% out %}-izing my site for the purpose of automatically preventing [runts](https://forum.affinity.serif.com/index.php?/topic/75751-widows-orphans-runts-%C2%A0hyphenation-better-terminology#:~:text={{ highlight_text }}){% out %} in text. Like its name would suggest, it's a simple Jekyll filter that can be used to replace the last instance of a substring within a given string. It's also my first ever published Ruby gem!&nbsp;:tada:
