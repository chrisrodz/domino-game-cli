# Caribbean Domino Game Rules

## Game Overview

Caribbean-style domino games, primarily based on Puerto Rican "Doscientos" rules with influences from Dominican and Jamaican variations.

## Equipment & Setup

- **Domino Set**: Double-Six set (28 tiles/bones)
- **Players**: 2-4 players
- **Starting**: Player with double-six (6-6) starts first game
- **Direction**: Counter-clockwise (right) - following Spanish Caribbean tradition

## Core Gameplay

### Starting a Game

1. Each player draws 7 dominoes
2. First player must play double-six if they have it
3. Subsequent rounds: winner of previous hand starts

### Playing Turns

1. Players must play matching dominoes to either end of the line
2. If unable to play: must pass (4-player) or draw from boneyard (2-3 player)
3. Game ends when:
   - One player plays all dominoes (goes out)
   - Game becomes blocked (no legal moves)

## Scoring System

### Primary Scoring Method: Point Accumulation

- **Target Score**: 100, 200 (traditional "Doscientos"), or 500 points with bonus
- **Round Scoring**: Count spots on remaining dominoes in losing players' hands
- **Winner**: First player/team to reach target score

#### 500 Point Game with Bonus Rules

- **Target**: 500 points
- **First Round Bonus**: +100 points to the team/player that wins the first round
- **Bonus Points**: Additional points awarded for special achievements:
  - **Double Out**: +50 points for going out with a double domino
  - **Domino**: +25 points for going out without drawing from boneyard
  - **Block Win**: +25 points for winning a blocked game with lowest count
  - **Shutout**: +100 points for preventing opponent from scoring any points in a round

### Round End Scenarios

#### 1. Player Goes Out

- Winner: Player who played their last domino
- Points: Sum of all spots on remaining dominoes in other players' hands
- Example: Remaining players have dominoes totaling 45 spots → winner gets 45 points

#### 2. Blocked Game ("Trancado")

- Winner: Player with lowest total spots on remaining dominoes
- Points: Sum of spots on ALL other players' dominoes
- Example: Player A has 12 spots, others have 15, 18, 22 → Player A wins and scores 55 points

### Special Scoring Rules

#### Partnership Variations (4 players)

- **Standard**: 1 point per hand won, first to 6 points wins
- **Key Bone**: 2 points if winning with the last playable domino when both ends are blocked
- **Reset Rule**: If losing team wins a hand, score resets to 0-0

#### Puerto Rican "Chiva" Variation

- Must win 4 consecutive games to win match
- No cumulative scoring - consecutive wins only

## Data Structure Requirements

### Domino Representation

- Each domino: two numbers (0-6)
- Total value: sum of both sides
- Example: [3|5] = 8 points, [6|6] = 12 points, [0|1] = 1 point

### Score Calculation Functions Needed

1. `calculateDominoValue(domino)` → sum of both sides
2. `calculateHandTotal(dominoes[])` → sum of all domino values in hand
3. `determineRoundWinner(players[])` → lowest total wins in blocked game
4. `calculateRoundPoints(winner, allPlayers)` → sum of losers' remaining points

### Game State Requirements

- Track remaining dominoes per player
- Identify round end conditions (out vs blocked)
- Calculate cumulative scores toward target (100/200)
- Determine overall game winner

## Implementation Priority

1. **Phase 2**: Core scoring logic and round management
2. **Phase 3**: Photo capture for remaining dominoes
3. **Phase 4**: Computer vision for automatic point calculation
4. **Phase 5**: Manual entry fallback and score persistence

## Cultural Notes

- Dominoes is the national game of Puerto Rico
- Tables in town squares are traditional gathering places
- Strong emphasis on community and social interaction
- Game rules passed down through generations with regional variations
