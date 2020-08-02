---
title: Portfolio
h1: Sean's Portfolio
h2: Check out some examples of my past work
place-in-menu: 2
tags: wide css
---
{%- assign items = site.portfolio-items | reverse -%}
{%- for item in items -%}
{% unless item.tags contains 'retired' %}
<div class="pf-item" id="{{ item.id | remove: '/portfolio-items/' }}">
  <div class="pf-img">
    <a href="{{ item.link }}" target="_blank" rel="noreferrer">
      {% include modules/image.html image=item.image title=item.title %}
    </a>
  </div>
  <div class="pf-text">
    <h2><a href="{{ item.link }}" target="_blank" rel="noreferrer">{{ item.title }}</a></h2>
    <h3>{{ item.source }} | {{ item.date | date: '%B %Y' | kill_runts }}</h3>
    {{ item.content | markdownify }}
  </div>
</div>
{% endunless %}
{%- endfor -%}