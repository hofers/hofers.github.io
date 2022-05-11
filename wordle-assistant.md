---
title: Wordle Assistant
h1: Wordle Assistant
h2: Check what valid words remain based on your guesses
tags: css js
---
[WordleBot](https://www.nytimes.com/interactive/2022/upshot/wordle-bot.html){% out %} uses the word pool to determine valid guesses so this must not be cheating!

Enter a guess and tap a tile to change its color. Hit enter/return to apply the guess and move to the next line. 

Press <span style="color:#538d4e;">**Get Guesses**</span> for a selection of the best possible guesses (note: doing this probably *is* cheating 😉).

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
</div>

<input type="text" class="dummy" id="dummy">
<div id="thinking" class="thinking hidden"><p>Thinking...</p></div>

<div class="button-container">
  <button onclick="requestNewGuesses()">Get Guesses</button>
</div>
<div class="word-list" id="guess-list"></div>

<p id="remaining" style="text-align: center; margin-top: 1rem;">Valid Words Remaining: 2309</p>
<div class="word-list" id="solution-list"></div>