onmessage = function(e) {
  let scoredGuesses = [];
  const solutions = e.data.currentSolutionList;
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
  const guesses = ALL_GUESSES.split(" ");
  const numSolutions = solutions.length;
  const solutionCodes = new Uint8Array(numSolutions * 5);
  for (let i = 0; i < numSolutions; i++) {
    for (let j = 0; j < 5; j++) {
      solutionCodes[i * 5 + j] = solutions[i].charCodeAt(j) - 97;
    }
  }
  const guessCodes = new Uint8Array(5);
  const marks = new Uint8Array(5);
  const unspent = new Uint8Array(26);
  const counts = new Int32Array(243);
  const seenPatterns = new Uint8Array(243);
  scoredGuesses = guesses.map(guess => {
    for (let j = 0; j < 5; j++) {
      guessCodes[j] = guess.charCodeAt(j) - 97;
    }
    let numGroups = 0;
    for (let i = 0; i < numSolutions; i++) {
      const base = i * 5;
      for (let j = 0; j < 5; j++) {
        const solutionCode = solutionCodes[base + j];
        if (guessCodes[j] === solutionCode) {
          marks[j] = 2;
        } else {
          marks[j] = 0;
          unspent[solutionCode]++;
        }
      }
      let pattern = 0;
      for (let j = 0; j < 5; j++) {
        let mark = marks[j];
        if (mark === 0 && unspent[guessCodes[j]] > 0) {
          unspent[guessCodes[j]]--;
          mark = 1;
        }
        pattern = pattern * 3 + mark;
      }
      for (let j = 0; j < 5; j++) {
        unspent[solutionCodes[base + j]] = 0;
      }
      if (counts[pattern] === 0) {
        seenPatterns[numGroups++] = pattern;
      }
      counts[pattern]++;
    }
    let total = 0;
    let maxGroupLength = 0;
    for (let i = 0; i < numGroups; i++) {
      const groupCount = counts[seenPatterns[i]];
      total += (Math.log2(numSolutions / groupCount) * groupCount);
      if (groupCount > maxGroupLength) {
        maxGroupLength = groupCount;
      }
      counts[seenPatterns[i]] = 0;
    }
    return {
      guess: guess,
      bits: (total / numSolutions).toFixed(2),
      numGroups: numGroups,
      maxGroupLength: maxGroupLength
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
   * the best guess, only return remaining solutions as guesses, up to 10.
   * 
   * Otherwise, if the user has toggled Hard Mode on, only return the top ten
   * remaining guesses that are valid in Hard Mode.
   * 
   * Otherwise, simply return the top 10 guesses.
   */
  if (solutions.every(
    w => scoredGuesses.find(
      g => g.guess === w 
      && g.bits === scoredGuesses[0].bits
    )
  )) {
    scoredGuesses = scoredGuesses.filter(word => solutions.includes(word.guess));
  } else if (e.data.hardMode) {
    scoredGuesses = scoredGuesses.filter(word => e.data.allValidGuesses.includes(word.guess)).slice(0, 10);
  } else {
    scoredGuesses = scoredGuesses.slice(0, 10);
  }
  postMessage(scoredGuesses);
}
