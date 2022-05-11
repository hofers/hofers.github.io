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
  scoredGuesses = e.data.allGuesses.map(guess => {
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
  scoredGuesses.sort((a, b) => b.numGroups === a.numGroups 
    ? a.maxGroupLength - b.maxGroupLength 
    : b.numGroups - a.numGroups
  );
  scoredGuesses = scoredGuesses.filter(
    g => g.numGroups === scoredGuesses[0].numGroups
  );
  scoredGuesses = scoredGuesses.sort(
    (a, b) => e.data.currentSolutionList.includes(a.guess) 
      ? -1 
      : e.data.currentSolutionList.includes(b.guess) 
        ? 1 : 0
  ).slice(0, 5);
  if (e.data.currentSolutionList.every(w => scoredGuesses.find(g => g.guess === w))) {
    scoredGuesses = e.data.currentSolutionList.map(word => ({guess: word, maxGroupLength: 1}));
  }
  postMessage(scoredGuesses);
}