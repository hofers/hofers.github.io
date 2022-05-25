onmessage = function(e) {
  let scoredGuesses = [];
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
    let groupCounts = Object.values(
      e.data.currentSolutionList.map(
        word => {
          let tempWord = word;
          return [...guess].map((letter, index) => {
            if (tempWord[index] === letter) {
              tempWord = tempWord.replace(letter, '.');
              return 'g';
            } else if (tempWord.includes(letter)) {
              tempWord = tempWord.replace(letter, '.');
              return 'y';
            } else {
              return 'b';
            }
          }).join('')
        }
      ).reduce(function (acc, curr) {
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