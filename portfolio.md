---
title: Portfolio
h1: Sean's Portfolio
h2: Check out some examples of my past work
tags: is-in-menu wide
css: portfolio
---
{% assign items = site.portfolio-items | reverse %}
{% for item in items %}
<div class="pf-item" id="{{ item.id | remove: '/portfolio-items/' }}">
  <div class="pf-text">
    <h2 class="pf-item-title"><a href="{{ item.link }}" target="_blank" rel="noreferrer">{{ item.title }}</a></h2>
    <h3>{{ item.source }} | {{ item.date | date: '%B %Y' }}</h3>
    {{ item.content | markdownify }}
  </div>
  <div class="pf-img">
    <a href="{{ item.link }}" target="_blank" rel="noreferrer"><img
        src="{{ item.image }}" alt="{{ item.title }}"></a>
  </div>
</div>
{% endfor %}