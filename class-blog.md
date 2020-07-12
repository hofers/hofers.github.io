---
categories: [class]
layout: page
title: "Class Blog"
h1: "Class Blog"
h2: "A blog for my Intro to Game Studies class"
---
Shortly efore starting at [Minted](https://www.minted.com){% out %} in October 2019, I had started taking an Intro to Game Studies class at [San Jose State University](https://www.sjsu.edu/){% out %}. Part of that class was maintaining a blog, which I've retained here for posterity.
<ul>
  {% assign class_posts = site.categories['class'] | reverse %}
  {%- for post in class_posts -%}
  <li>
    <a href="{{ post.url }}"> {{ post.title }} </a>
    | {{ post.date | date: '%B %d, %Y'}}
  </li>
  {%- endfor -%}
</ul>