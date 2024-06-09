onmessage = function(e) {
  let scoredGuesses = [];
  const solutions = e.data.currentSolutionList;
  const hardMode = e.data.hardMode;
  const solveWeight = 1 + ((1 / solutions.length) * 0.25);
  /**
   * Return a pre-calculated response for the first 
   * guess since it's always the same initial state.
   */
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
  /**
   * Otherwise, score every possible guess:
   * 
   * For each guess, divide the remaining solutions into groups,
   * based on the pattern of colors returned for all 5 tiles
   * (e.g. 'bbgyb' for guess: 'HELLO' for solution 'ALLAY')
   * and record the size of each of these groups.
   * 
   * Then, calculate and record the bits of information for each
   * guess based on these group sizes. This is the total information
   * derived from all of the group sizes divided by the number
   * of remaining solutions. The information derived from a given
   * group size is equal to the size of the group multiplied by
   * the log2 of the quotient of the number of solutions remaining
   * over the size of the current group. The bits of information
   * corresponding to each guess can be considered its "score".
   */
  scoredGuesses = ALL_GUESSES.split(" ").map(guess => {
    const groupCounts = Object.values(
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
    const bits = groupCounts.reduce(
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
  /**
   * Sort the scored guesses in descending order.
   * (i.e. highest scores first)
   */
  scoredGuesses.sort((a, b) => 
    solutions.includes(a.guess) 
      ? solutions.includes(b.guess) 
        ? (b.bits * solveWeight) - (a.bits * solveWeight)
        : b.bits - (a.bits * solveWeight)
      : solutions.includes(b.guess) 
        ? (b.bits * solveWeight) - a.bits
        : b.bits - a.bits
  );
  /**
   * If every remaining solution has a guess score that's tied with
   * the best guess, or if the user is playing in Hard Mode,
   * only return remaining solutions as guesses, up to 10.
   * 
   * Otherwise, simply return the top 10 guesses.
   */
  if (hardMode || solutions.every(
    w => scoredGuesses.find(
      g => g.guess === w 
      && g.bits === scoredGuesses[0].bits
    )
  )) {
    scoredGuesses = scoredGuesses.filter(word => solutions.includes(word.guess)).slice(0, 10);
  } else {
    scoredGuesses = scoredGuesses.slice(0, 10);
  }
  postMessage(scoredGuesses);
}
