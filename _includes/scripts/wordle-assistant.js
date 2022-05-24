{%- include snippets/wordle-solutions.js -%}
// include ALL_SOLUTIONS

var currentSolutionList = ALL_SOLUTIONS.split(" ");
var currentRules = {
  includes: [],
  excludes: [],
};
var currentRuleRegex = /\b.....\b/g;
var scoredGuesses = [];
var workerBlob = null;
var solver = null;

function startLoading() {
  document.getElementById('thinking').className = 'thinking';
}

function stopLoading() {
  document.getElementById('thinking').className = 'thinking hidden';
}

function applyNewGuess(guess, response) {
  let occurrences = [...guess].reduce((a, c, i) => {
    if (response[i] !== 'b') {
      a[c] ? a[c]++ : a[c] = 1;
    }
    return a;
  }, {});
  [...response].forEach((letter, index) => {
    let currentLetterIncludes = currentRules.includes.find(e => e.letter === guess[index]);
    switch (letter) {
      case 'b':
        if (currentLetterIncludes) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'n';
        } else {
          currentRules.excludes.push(guess[index]);
          currentRules.excludes = [...new Set(currentRules.excludes)];
        }
        break;
      case 'y':
        if (currentLetterIncludes) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'n';
          currentRules.includes.find(e => e.letter === guess[index]).occurrences = (
            Math.max(currentLetterIncludes.occurrences, occurrences[guess[index]])
          );
        } else {
          currentRules.includes.push({
            letter: guess[index],
            location: ['u', 'u', 'u', 'u', 'u'],
            occurrences: occurrences[guess[index]]
          })
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'n';
        }
        break;
      case 'g':
        if (currentLetterIncludes) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'y';
          currentRules.includes.find(e => e.letter === guess[index]).occurrences = (
            Math.max(currentLetterIncludes.occurrences, occurrences[guess[index]])
          );
        } else {
          currentRules.includes.push({
            letter: guess[index],
            location: ['u', 'u', 'u', 'u', 'u'],
            occurrences: occurrences[guess[index]]
          })
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'y';
        }
        break;
    }
  })
  updateRegex();
}

function updateRegex() {
  let regexString = '';
  let substring = '';
  let unplacedLetters = [];

  for (let i = 0; i < 5; i++) {
    if (currentRules.includes.find(e => e.location[i] === 'y')) {
      regexString += currentRules.includes.find(e => e.location[i] === 'y').letter;
      if (currentRules.includes.find(e => e.location[i] === 'n')) {
        for (const inclusionRule of currentRules.includes.filter(e => e.location[i] === 'n')) {
          substring += inclusionRule.letter;
        }
        unplacedLetters.push(...substring);
        substring = '';
      }
    } else if (currentRules.includes.find(e => e.location[i] === 'n')) {
      for (const inclusionRule of currentRules.includes.filter(e => e.location[i] === 'n')) {
        substring += inclusionRule.letter;
      }
      regexString += '[^' + substring + ']';
      unplacedLetters.push(...substring);
      substring = '';
    } else {
      regexString += '.';
    }
  }
  if (currentRules.excludes.length > 0) {
    regexString = regexString.replace(/\[\^/g, '[^' + currentRules.excludes.join(''));
    regexString = regexString.replace(/\./g, '[^' + currentRules.excludes.join('') + ']');
  }
  for (const letter of unplacedLetters) {
    let occurrences = currentRules.includes.find(e => e.letter === letter).occurrences;
    let partialString = '(?=';
    for (let i = 0; i < occurrences; i++) {
      partialString += '[^' + letter + ' ]*' + letter;
    }
    regexString = partialString + '[^' + letter + ' ]*\\b)' + regexString;
  }
  currentRuleRegex = RegExp('\\b' + regexString + '\\b', 'g');
  applyRegex();
}

function applyRegex() {
  currentSolutionList = [...ALL_SOLUTIONS.matchAll(currentRuleRegex)].map(word => word[0]);
  updateDisplayedSolutionList();
}

function requestNewGuesses() {
  startLoading();
  solver.postMessage({
    currentSolutionList: currentSolutionList,
  })
}

function clearGuesses() {
  currentSolutionList = ALL_SOLUTIONS.split(" ");
  currentRules = {
    includes: [],
    excludes: [],
  };
  currentRuleRegex = /\b.....\b/g;
  scoredGuesses = [];
}

function updateDisplayedSolutionList() {
  document.getElementById('remaining').innerHTML = 'Valid Words Remaining: ' + currentSolutionList.length;
  let solutionListDiv = document.getElementById("solution-list");
  let result = '';
  solutionListDiv.innerHTML = '';
  for (const word of currentSolutionList) {
    result += '<div class="word">' + word + '</div>'
  }
  solutionListDiv.innerHTML = result;

  let guessListDiv = document.getElementById("guess-list");
  guessListDiv.innerHTML = '';
}

function updateDisplayedGuessList() {
  let guess = '';
  let result = '';
  let guessListDiv = document.getElementById("guess-list");
  guessListDiv.innerHTML = '';
  for (const word of scoredGuesses) {
    guess = word.maxGroupLength === scoredGuesses[0].maxGroupLength &&
      word.numGroups === scoredGuesses[0].numGroups ?
      word.guess + " ☑️" : word.guess;
    result += '<div class="word guess">' + guess + '</div>'
  }
  guessListDiv.innerHTML = result;
  stopLoading();
}

document.addEventListener("DOMContentLoaded", function () {
  workerBlob = new Blob([
    document.getElementById('worker').textContent
  ], {
    type: "text/javascript"
  })
  solver = new Worker(window.URL.createObjectURL(workerBlob));
  document.addEventListener('keydown', (event) => {
    let allTiles = Array.from(document.getElementsByClassName('tile'));
    let activeGuessTiles = allTiles.filter(tile => tile.dataset.guessStatus === '1');
    let tileToUpdate = activeGuessTiles.find(e => e.innerHTML === '');
    if (!tileToUpdate)
      tileToUpdate = allTiles.find(e => e.innerHTML === '');
    if (event.key.length == 1 && event.key.match(/[a-z]/i)) {
      if (tileToUpdate.dataset.guessStatus === '1') {
        tileToUpdate.innerHTML = event.key;
        tileToUpdate.className += ' not-in-word';
        tileToUpdate.dataset.locationValue = 'b';
      }
    } else if (event.key === 'Backspace') {
      tileToUpdate = activeGuessTiles[
        (allTiles.indexOf(tileToUpdate) - 1) % 5
      ];
      if (!tileToUpdate)
        return;
      tileToUpdate.innerHTML = '';
      tileToUpdate.className = 'tile';
      tileToUpdate.dataset.locationValue = '';
    } else if (event.key === 'Enter') {
      let guess = activeGuessTiles.reduce((p, c) => p + c.innerText, '').toLowerCase();
      if (guess.length < 5)
        return;
      let response = activeGuessTiles.reduce((p, c) => p + c.dataset.locationValue, '');
      applyNewGuess(guess, response);
      for (const tile of activeGuessTiles) {
        tile.dataset.guessStatus = '2';
      }
      let newTiles = allTiles.filter(tile => tile.dataset.guessStatus !== '2').slice(0, 5);
      for (const tile of newTiles) {
        tile.dataset.guessStatus = '1';
      }
    }
  })

  for (const el of document.getElementsByClassName('tile')) {
    el.addEventListener('click', () => {
      document.getElementById('dummy').focus();
      if (el.classList.length !== 1 && el.dataset.guessStatus === '1') {
        if (el.dataset.locationValue === 'b') {
          el.className = 'tile elsewhere-in-word';
          el.dataset.locationValue = 'y';
        } else if (el.dataset.locationValue === 'y') {
          el.className = 'tile correctly-placed';
          el.dataset.locationValue = 'g';
        } else {
          el.className = 'tile not-in-word';
          el.dataset.locationValue = 'b';
        }
      }
    })
  }

  solver.onmessage = function (e) {
    scoredGuesses = e.data;
    updateDisplayedGuessList();
  }
}); 
{%- include snippets/wordle-script-tags.html -%}
{%- include snippets/wordle-guesses.js -%}
// include ALL_GUESSES and ALL_SOLUTIONS
onmessage = function(e) {
  var scoredGuesses = [];
  if (e.data.currentSolutionList.length === 2309) {
    scoredGuesses = [{
      guess: 'crane',
      maxGroupLength: 1
    },
    {
      guess: 'crate',
      maxGroupLength: 2
    },
    {
      guess: 'slate',
      maxGroupLength: 2
    }];
    postMessage(scoredGuesses);
    return;
  }
  scoredGuesses = ALL_GUESSES.split(" ").map(guess => {
    var groupCounts = Object.values(
      e.data.currentSolutionList.map(
        word => [...guess].map((letter, index) => {
          if (word[index] === letter) {
            return 'g';
          } else if (word.includes(letter)) {
            return 'y';
          } else {
            return 'b';
          }
        })
          .join('')
      )
        .reduce(function (acc, curr) {
          return acc[curr] ? ++acc[curr] : acc[curr] = 1, acc
        }, {})
    );
    return {
      guess: guess,
      numGroups: groupCounts.length,
      maxGroupLength: Math.max(...groupCounts)
    };
  })
  // sort priority: 
  // 1. greatest numGroups (most unique results)
  // 2. lowest max group length (minimize size of next solution set)
  // 3. is included in solution set
  // 4. commonness of words in typical speech (default order of list)
  scoredGuesses.sort((a, b) => 
    b.numGroups === a.numGroups
    ? a.maxGroupLength === b.maxGroupLength
      ? e.data.currentSolutionList.includes(a.guess)
        ? -1
        : e.data.currentSolutionList.includes(b.guess)
          ? 1
          : 0
      : a.maxGroupLength - b.maxGroupLength
    : b.numGroups - a.numGroups
  );
  if (e.data.currentSolutionList.every(
    w => scoredGuesses.find(
      g => g.guess === w 
      && g.numGroups === scoredGuesses[0].numGroups
    )
  )) {
    scoredGuesses = e.data.currentSolutionList.map(word => ({guess: word, maxGroupLength: 1}));
  } else {
    scoredGuesses = scoredGuesses.slice(0, 5);
  }
  postMessage(scoredGuesses);
}