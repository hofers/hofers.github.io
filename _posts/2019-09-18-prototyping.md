---
layout: post
categories: [class]
title: "First Game Prototype: Hexadecimate"
subtitle: "The process for my first rough prototype"
image: "/assets/images/game-pieces.jpg"
---
## *Hexadecimate*

<!-- e -->
***

### First Session

For our first in-class prototpying session, I worked with one of my classmates on a basic prototype for a board game involving [Grid Movement](https://boardgamegeek.com/boardgamemechanic/2676/grid-movement){:target='_blank' :rel='noreferrer'}, [Action Points](https://boardgamegeek.com/boardgamemechanic/2001/act-01-action-points){:target='_blank' :rel='noreferrer'}, and [Card Play](https://boardgamegeek.com/boardgamemechanic/2857/res-06-card-play){:target='_blank' :rel='noreferrer'} mechanics. The initial version pit two players -- <span style="color:red;">Red</span> and <span style="color:blue;">Blue</span> -- against each other in a death match. Players began with five units each arranged on a square grid. Full rules and a basic board layout can be found below.

Rules              |  Board 
:-------------------------:|:-------------------------:
![First Draft Rules](/assets/images/draft-1-rules.jpg){:width="100%"}  |  ![First Draft Board](/assets/images/draft-1-board.jpg){:width="100%"}

After playing this version a couple times, I noted that gameplay felt slow and uneventful. Combat was infrequent and not particularly interesting, and winning felt arbitrary. The <span style="color:green;">General</span> mechanic also seemed thematically interesting but proved not to be in regards to gameplay or decision-making.

***

### Second Session

My second session was played at home with my partner, and for it I made a few distinct rule changes. Most notably, I altered the board layout, changing it from a square-based board to a hex-based board (which later inspired its name). Players now start with 7 units each, and there are now a total of 4 <span style="color:purple;">Neutral</span> units on the board -- two at each side -- which can be recruited at a cost of one move. This was an attempt to create a secondary objective that would create conflict and lead to more interesting early-game scenarios. 

During this session, I also experimented with a couple different ways for players to <span style="color:#e0bd02;">augment</span> their units during combat, all having to do with unit positioning. This was an attempt at making combat more tactical and interesting by allowing players to control some of the randomness of the system introduced by the Card Play mechanic.

I rewrote the rules after this session; they're included below alongside an image of the updated board.

Rules              |  Board 
:-------------------------:|:-------------------------:
![Second Draft Rules](/assets/images/draft-2-rules.jpg){:width="100%"}  |  ![Second Draft Board](/assets/images/game-board.jpg){:width="100%"}

By the end of this session I had settled on a fairly simple battle <span style="color:#e0bd02;">augmentation</span> mechanic: the two spaces adjacent to both primary units in combat are available for either player to use as for <span style="color:#e0bd02;">augmentation</span>. During an attack, occupying an <span style="color:#e0bd02;">augmentation</span> space allows a player to draw cards for each allied unit in combat, rather than just one. 

![Game Pieces](/assets/images/game-pieces.jpg){:width="100%"}
*e.g. Each player has a unit in an <span style="color:#e0bd02;">augmentation space</span>. When <span style="color:red;">Red</span> attacks <span style="color:blue;">Blue</span>, they can each choose to use that unit to <span style="color:#e0bd02;">augment</span> their attack/defense. Attacking with additional units costs 1 move per additional unit used.*

***

### Third Session

Going into my third play session, I had a couple ideas for ways to improve gameplay. Namely, the game still felt a bit slow, and I wanted to allow for more interesting defensive strategies, because the current best strategy was often just "send all your units directly at the enemy". This initially lead me to try implementing an [Area Control](https://boardgamegeek.com/boardgamemechanic/2080/area-control-area-influence){:target='_blank' :rel='noreferrer'} mechanic, where occupying certain spaces gave a defensive <span style="color:#e0bd02;">augmentation</span> of +1 to all surrounding units. However, this implementation actually seemed to cause larger issues than it solved: the best strategy immediately became "occupy your closest defensive spaces and wait". 

My next attempt was to change the objective of the game from routing the enemy to occupying a space at the opposite side of the board. This was done hoping it would allow for a more strategic game, as each player would have two objectives: offense and defense. However, it quickly became clear that this would likely cause issues due to high early unit mobility and the shape of the board. A few matches of this revealed that it was rather easy to end the game on turn 2 or 3 if the enemy made the mistake of not covering their goal space from all 4 possible directions, which meant combat would essentially be limited to 3 players' remaining units. 

After these attempts were unsuccessful, I took a classmate's suggestion and tried simply shrinking the board (in reality, we just ignored hexes on the board that we already hed). This suggestion proved to be the best one, as it cut down on a significant amount of travel time that was required to get combat going, and allowed for faster strategic adaptations. The board from this iteration is shown below.

![Final Board](/assets/images/final-board.jpg){:width="100%"} *Final Game Board*

The final rules can be found in my previous blog post, [Hexadecimate Rules](/blog/game-rules).