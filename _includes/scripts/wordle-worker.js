onmessage = function(e) {
  let scoredGuesses = [];
  let solutions = e.data.currentSolutionList;
  if (solutions.length === 2309) {
    scoredGuesses = [
      {guess: 'crane', bits: '5.74', numGroups: 142, maxGroupLength: 263},
      {guess: 'slate', bits: '5.86', numGroups: 146, maxGroupLength: 221},
      {guess: 'crate', bits: '5.84', numGroups: 148, maxGroupLength: 246},
      {guess: 'slant', bits: '5.49', numGroups: 131, maxGroupLength: 316},
      {guess: 'trace', bits: '5.83', numGroups: 150, maxGroupLength: 246},
      {guess: 'reast', bits: '5.87', numGroups: 147, maxGroupLength: 226},
      {guess: 'salet', bits: '5.84', numGroups: 148, maxGroupLength: 221},
      {guess: 'soare', bits: '5.89', numGroups: 127, maxGroupLength: 182},
      {guess: 'raise', bits: '5.88', numGroups: 132, maxGroupLength: 167},
      {guess: 'irate', bits: '5.83', numGroups: 124, maxGroupLength: 193}
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
  let solveWeight = 1 + (1 / solutions.length);
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