onmessage = function(e) {
  let scoredGuesses = [];
  let solutions = e.data.currentSolutionList;
  let solveWeight = 1 + ((1 / solutions.length) * 0.75);
  if (solutions.length === 3189) {
    scoredGuesses = [
      {guess: "tarse", bits: "5.89", numGroups: 158, maxGroupLength: 321, checked: 1},
      {guess: "tiare", bits: "5.86", numGroups: 150, maxGroupLength: 276},
      {guess: "sater", bits: "5.85", numGroups: 151, maxGroupLength: 321},
      {guess: "roate", bits: "5.84", numGroups: 133, maxGroupLength: 253},
      {guess: "raise", bits: "5.83", numGroups: 137, maxGroupLength: 243},
      {guess: "soare", bits: "5.82", numGroups: 134, maxGroupLength: 238},
      {guess: "raile", bits: "5.82", numGroups: 134, maxGroupLength: 253},
      {guess: "taler", bits: "5.81", numGroups: 145, maxGroupLength: 288},
      {guess: "caret", bits: "5.80", numGroups: 156, maxGroupLength: 343},
      {guess: "salet", bits: "5.80", numGroups: 161, maxGroupLength: 314},
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
