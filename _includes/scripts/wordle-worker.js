onmessage = function(e) {
  let scoredGuesses = [];
  let solutions = e.data.currentSolutionList;
  let solveWeight = 1 + (1 / solutions.length);
  if (solutions.length === 2309) {
    scoredGuesses = [
      {guess: 'crate', bits: '5.84', numGroups: 148, maxGroupLength: 246, checked: 1},
      {guess: 'trace', bits: '5.83', numGroups: 150, maxGroupLength: 246, checked: 1},
      {guess: 'slate', bits: '5.86', numGroups: 146, maxGroupLength: 221, checked: 1},
      {guess: 'saine', bits: '5.76', numGroups: 136, maxGroupLength: 207, checked: 1},
      {guess: 'crane', bits: '5.74', numGroups: 142, maxGroupLength: 263, checked: 1},
      {guess: 'salet', bits: '5.84', numGroups: 148, maxGroupLength: 221},
      {guess: 'saice', bits: '5.69', numGroups: 124, maxGroupLength: 211},
      {guess: 'slane', bits: '5.77', numGroups: 133, maxGroupLength: 225},
      {guess: 'zaire', bits: '5.04', numGroups: 86, maxGroupLength: 261},
      {guess: 'craze', bits: '4.94', numGroups: 90, maxGroupLength: 369}
    ];
    postMessage(scoredGuesses);
    return;
  }
  scoredGuesses = ALL_GUESSES.split(" ").map(guess => {
    let groupCounts = Object.values(
      solutions.map(
        solution => {
          let tempWord = solution;
          return [...guess].map((letter, index) => {
            if (tempWord[index] === letter) {
              tempWord = tempWord.replace(letter, '.');
              return 'g';
            } else if (tempWord.includes(letter) && !(guess[tempWord.indexOf(letter)] === letter)) {
              tempWord = tempWord.replace(letter, '.');
              return 'y';
            } else {
              return 'b';
            }
          }).join('');
        }
      ).reduce(function (acc, curr) {
        return acc[curr] ? ++acc[curr] : acc[curr] = 1, acc
      }, {})
    );
    let bits = groupCounts.reduce(
      (a, c) => a += (Math.log2(solutions.length / c) * c),
      0
    ) / solutions.length;
    return {
      guess: guess,
      bits: bits.toFixed(2),
      numGroups: groupCounts.length,
      maxGroupLength: Math.max(...groupCounts)
    };
  })
  scoredGuesses.sort((a, b) => 
    solutions.includes(a.guess) 
      ? solutions.includes(b.guess) 
        ? (b.bits * solveWeight) - (a.bits * solveWeight)
        : b.bits - (a.bits * solveWeight)
      : solutions.includes(b.guess) 
        ? (b.bits * solveWeight) - a.bits
        : b.bits - a.bits
  );
  if (solutions.every(
    w => scoredGuesses.find(
      g => g.guess === w 
      && g.bits === scoredGuesses[0].bits
    )
  )) {
    scoredGuesses = scoredGuesses.filter(word => solutions.includes(word.guess));
  } else {
    scoredGuesses = scoredGuesses.slice(0, 10);
  }
  postMessage(scoredGuesses);
}