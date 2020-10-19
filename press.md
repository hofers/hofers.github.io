---
title: Press
h1: Press
h2: News stories about some of my work
---
<ul>
  {%- for item in site.press-items -%}
  <li>
    <a href="{{ item.link }}" target="_blank" rel="noreferrer">{{ item.title }} | {{ item.source }}</a>
  </li>
  {%- endfor -%}
</ul>