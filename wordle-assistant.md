---
title: Wordle Assistant
h1: Wordle Assistant
h2: Check what valid words remain based on your guesses
tags: css js
---
[WordleBot](https://www.nytimes.com/interactive/2022/upshot/wordle-bot.html){% out %} uses the word pool to determine valid guesses so this must not be cheating!

<div class="grid">
  <div class="tile" data-guess-status="1" id="11"></div>
  <div class="tile" data-guess-status="1" id="12"></div>
  <div class="tile" data-guess-status="1" id="13"></div>
  <div class="tile" data-guess-status="1" id="14"></div>
  <div class="tile" data-guess-status="1" id="15"></div>
  <div class="tile" id="21"></div>
  <div class="tile" id="22"></div>
  <div class="tile" id="23"></div>
  <div class="tile" id="24"></div>
  <div class="tile" id="25"></div>
  <div class="tile" id="31"></div>
  <div class="tile" id="32"></div>
  <div class="tile" id="33"></div>
  <div class="tile" id="34"></div>
  <div class="tile" id="35"></div>
  <div class="tile" id="41"></div>
  <div class="tile" id="42"></div>
  <div class="tile" id="43"></div>
  <div class="tile" id="44"></div>
  <div class="tile" id="45"></div>
  <div class="tile" id="51"></div>
  <div class="tile" id="52"></div>
  <div class="tile" id="53"></div>
  <div class="tile" id="54"></div>
  <div class="tile" id="55"></div>
  <div class="tile" id="61"></div>
  <div class="tile" id="62"></div>
  <div class="tile" id="63"></div>
  <div class="tile" id="64"></div>
  <div class="tile" id="65"></div>
</div>

<input type="text" class="dummy" id="dummy">

<p id="remaining"></p>
<div class="word-list" id="word-list"></div>