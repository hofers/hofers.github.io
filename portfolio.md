---
layout: page
title: Portfolio
h1: Sean's Portfolio
h2: Check out some examples of my past work
is-in-menu: true
wide: true
---
{% assign items = site.portfolio-items | reverse %}
{% for item in items %}
<div class="pf-item" id="{{ item.name }}">
  <div class="pf-text">
    <h2 class="pf-item-title"><a href="{{ item.link }}" target="_blank" rel="noreferrer">{{ item.title }}</a></h2>
    <h3>{{ item.subtitle }}</h3>
    <p>
    {{ item.content | markdownify }}
    </p>
  </div>
  <div class="pf-img">
    <a href="{{ item.link }}" target="_blank" rel="noreferrer"><img
        src="{{ item.image }}" alt="{{ item.title }}"></a>
  </div>
</div>
{% endfor %}