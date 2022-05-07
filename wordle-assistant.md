---
title: Wordle Assistant
h1: Wordle Assistant
h2: Check what valid words remain based on your guesses
tags: css js
---
[WordleBot](https://www.nytimes.com/interactive/2022/upshot/wordle-bot.html){% out %} uses the word pool to determine valid guesses so this must not be cheating!

Enter a guess and tap a tile to change its color. Hit enter/return to apply the guess and move to the next line.

<div class="grid">
  <div class="tile" data-guess-status="1"></div>
  <div class="tile" data-guess-status="1"></div>
  <div class="tile" data-guess-status="1"></div>
  <div class="tile" data-guess-status="1"></div>
  <div class="tile" data-guess-status="1"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
  <div class="tile"></div>
</div>

<input type="text" class="dummy" id="dummy">

<p id="remaining" style="text-align: center;">Valid Words Remaining: 2309</p>
<div class="word-list" id="word-list"></div>