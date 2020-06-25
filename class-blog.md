---
layout: page
title: "Class Blog"
h1: "Class Blog"
h2: "A blog for my Intro to Game Studies class"
tags: has-italics
---
<ul>
  {%- for post in site.posts -%}
  <li>
    <a href="{{ post.url }}"> {{ post.title }} </a>
    | {{ post.date | date: '%B %d, %Y'}}
  </li>
  {%- endfor -%}
</ul>