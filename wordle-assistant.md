---
title: Wordle Assistant
h1: Wordle Assistant
h2: Check what valid words remain based on your guesses
tags: css min-js
---
[WordleBot](https://www.nytimes.com/interactive/2022/upshot/wordle-bot.html){% out %} uses the word pool to determine valid remaining solutions so this must not be cheating!

Enter a guess and tap a tile to change its color. Hit enter/return to apply the guess, move to the next line and print the remaining solutions below.

Press <span style="color:#538d4e;">**Get Guesses**</span> for a selection of the best possible guesses (note: doing this probably *is* cheating 😉).

Note: this tool is not actively maintained may no longer provide the best guesses possible.

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

<div class="button-container">
  <button onclick="requestNewGuesses()">Get Guesses</button>
</div>
<div id="footnotes" class="center-text small-text hidden">
  <p>Guesses with &nbsp;☑️&nbsp; are tied for the best score.</p>
  <p>Guesses with &nbsp;✨&nbsp; are possible solutions.</p>
</div>
<div id="thinking" class="center-text hidden"><p>Thinking...</p></div>
<div id="guess-header" class="guess-header hidden">
  <div>✨</div>
  <div>☑️</div>
  <div>Guess</div>
  <div class="smallish-text">Bits</div>
  <div class="smallish-text"># Groups</div>
  <div class="smallish-text">Max Group Size</div>
</div>
<div class="word-list" id="guess-list"></div>

<p id="remaining" style="text-align: center; margin-top: 1rem;">Valid Solutions Remaining: 2309</p>
<div class="word-list" id="solution-list"></div>