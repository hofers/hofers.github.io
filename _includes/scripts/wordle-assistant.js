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
  document.getElementById('thinking').className = 'center-text';
  document.getElementById('footnotes').className = 'center-text small-text hidden';
}

function stopLoading() {
  document.getElementById('thinking').className = 'center-text hidden';
  document.getElementById('footnotes').className = 'center-text small-text'
  document.getElementById('guess-header').className = 'guess-header';
}

function applyNewGuess(guess, response) {
  let occurrences = [...guess].reduce((a, c, i) => {
    if (response[i] !== 'b') {
      a[c] ? a[c]++ : a[c] = 1;
    }
    return a;
  }, {});
  [...response].forEach((letter, index) => {
    let currentLetter = currentRules.includes.find(e => e.letter === guess[index]);
    switch (letter) {
      case 'b':
        if (currentLetter) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'n';
          currentRules.includes.find(e => e.letter === guess[index]).maxOccurrences = (
            Math.max(currentLetter.occurrences, occurrences[guess[index]])
          );
        } else {
          currentRules.excludes.push(guess[index]);
          currentRules.excludes = [...new Set(currentRules.excludes)];
        }
        break;
      case 'y':
        if (currentLetter) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'n';
          currentRules.includes.find(e => e.letter === guess[index]).occurrences = (
            Math.max(currentLetter.occurrences, occurrences[guess[index]])
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
        if (currentLetter) {
          currentRules.includes.find(e => e.letter === guess[index]).location[index] = 'y';
          currentRules.includes.find(e => e.letter === guess[index]).occurrences = (
            Math.max(currentLetter.occurrences, occurrences[guess[index]])
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
    let maxOccurrences = currentRules.includes.find(e => e.letter === letter).maxOccurrences || 5;
    let partialString = '(?=';
    for (let i = 0; i < occurrences; i++) {
      partialString += '[^' + letter + ' ]*' + letter;
    }
    regexString = partialString + '[^' + (maxOccurrences === occurrences ? letter : '') + ' ]*\\b)' + regexString;
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
    hardMode: document.getElementById('hardMode').checked,
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
    guess = word.bits === scoredGuesses[0].bits ? word.guess + " ☑️" : word.guess;
    result += '<div class="word guess">'
      + '<div>' + (currentSolutionList.includes(word.guess) ? "✨" : "") + '</div>'
      + '<div>' + (word.bits === scoredGuesses[0].bits || word.checked ? "☑️" : "") + '</div>'
      + '<div>' + word.guess + '</div>'
      + '<p class="smallish-text">' + word.bits + '</p>'
      + '<p class="smallish-text">' + word.numGroups + '</p>'
      + '<p class="smallish-text">' + word.maxGroupLength + '</p>'
      + '</div>'
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
