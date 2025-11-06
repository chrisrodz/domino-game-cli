# Tutorial Mode Plan: Teaching Players to Master Caribbean Dominoes

## Executive Summary

This plan outlines the implementation of an interactive Tutorial Mode that transforms the dominoes CLI game into an educational experience. The mode will analyze each turn, highlight optimal moves, explain strategic reasoning, and reference previous game actions to help players develop winning strategies.

---

## 1. Overview & Goals

### Primary Objectives
- **Teach Strategic Thinking**: Help players understand *why* certain moves are better than others
- **Build Intuition**: Connect current decisions to previous game state and future outcomes
- **Progressive Learning**: Start with basic concepts and advance to expert-level tactics
- **Real-Time Guidance**: Provide contextual hints during actual gameplay

### Success Criteria
- Players can identify high-value moves independently after 3-5 tutorial games
- Tutorial explanations reference specific previous moves in the game
- Strategic concepts are explained using game-winning dominoes theory
- Mode is toggleable and non-intrusive for experienced players

---

## 2. Game-Winning Dominoes Strategies (Research Summary)

Based on expert sources, the tutorial will teach these proven strategies:

### Core Strategies

#### 1. **Play Doubles Early**
- **Why**: Doubles are hardest to play (only match one number)
- **Example**: [6|6] can only connect to 6, while [6|3] can connect to 6 or 3
- **Timing**: Prioritize in early-mid game before board gets blocked

#### 2. **Play Heavy Tiles First**
- **Why**: Minimize points in hand if opponent wins
- **Example**: Playing [6|5] (11 pts) before [1|0] (1 pt) reduces penalty
- **Risk Management**: Essential for Caribbean scoring where all hands count

#### 3. **Maintain Balanced Hand**
- **Why**: More numbers = more play opportunities
- **Example**: Having [2|3], [3|5], [5|6] better than [6|6], [6|5], [6|4]
- **Card Counting**: Track which numbers appear frequently

#### 4. **Tile Counting & Memory**
- **Why**: Predict opponent capabilities
- **Mechanic**: Each number (0-6) appears exactly 8 times in the deck
- **Application**: If 7 tiles with "4" have been played and you have the 8th, opponents can't play on 4

#### 5. **Strategic Blocking**
- **Why**: Force opponents to pass, gain control
- **Technique**: Play tiles that make both board ends numbers opponent lacks
- **Advanced**: In teams, block opponents while keeping ally's numbers available

#### 6. **Endgame Tactics**
- **Why**: Different goals near round end
- **Leading**: Play defensively, keep low-value tiles
- **Behind**: Play aggressively, try to go out or block

### Advanced Tactics

#### 7. **Control the Board**
- Place tiles that give you more future options
- Create board ends matching your strongest suits

#### 8. **Team Coordination** (Caribbean 2v2 specific)
- Keep tiles that help your ally
- Block numbers opponents played recently
- Sacrifice high tiles if ally is close to going out

#### 9. **Offensive vs Defensive Play**
- **Offense**: Play high tiles quickly, aim to go out
- **Defense**: Keep versatile tiles, prevent opponent scoring

---

## 3. Tutorial Mode Architecture

### 3.1 Core Components

#### **TutorialEngine Class**
Manages the tutorial system with these responsibilities:

```python
class TutorialEngine:
    """Main tutorial orchestrator"""

    # Configuration
    enabled: bool                           # Toggle on/off
    difficulty_level: TutorialLevel         # BEGINNER, INTERMEDIATE, ADVANCED

    # Game Analysis
    move_analyzer: MoveAnalyzer             # Evaluates move quality
    strategy_advisor: StrategyAdvisor       # Suggests optimal plays
    game_historian: GameHistorian           # Tracks game state history

    # User Interaction
    hint_display: HintDisplay               # Formats and shows hints
    progress_tracker: ProgressTracker       # Tracks player improvement
```

#### **MoveAnalyzer Class**
Evaluates and scores potential moves:

```python
class MoveAnalyzer:
    """Analyzes move quality using strategic heuristics"""

    def analyze_move(self, domino, position, game_state) -> MoveAnalysis:
        """
        Returns comprehensive analysis including:
        - Strategic score (0-100)
        - Strategy categories applied (e.g., "heavy first", "blocking")
        - Risks and benefits
        - Better alternatives if available
        """

    def get_optimal_moves(self, valid_moves, game_state) -> List[MoveRanking]:
        """Returns moves ranked by strategic value"""

    def explain_move(self, move, game_state) -> str:
        """Generates natural language explanation"""
```

#### **StrategyAdvisor Class**
Provides contextual strategic advice:

```python
class StrategyAdvisor:
    """Generates strategic recommendations"""

    def suggest_move(self, valid_moves, game_state, history) -> MoveRecommendation:
        """
        Recommends best move with:
        - Primary strategy rationale
        - Reference to previous turns
        - Expected outcome
        - Alternative considerations
        """

    def detect_teachable_moments(self, game_state) -> List[Insight]:
        """Identifies opportunities to teach new concepts"""
```

#### **GameHistorian Class**
Maintains game history for contextual teaching:

```python
class GameHistorian:
    """Tracks all game state for contextual explanations"""

    moves_history: List[MoveRecord]         # All moves played
    board_states: List[BoardSnapshot]       # Board after each move
    tile_tracking: TileCounter              # Tracks which tiles played

    def get_previous_moves_with_number(self, number: int) -> List[MoveRecord]:
        """Find past moves involving a number"""

    def get_player_pattern(self, player_idx: int) -> PlayerPattern:
        """Analyze player's tile holdings based on passes/plays"""

    def explain_board_evolution(self) -> str:
        """Narrative of how board reached current state"""
```

#### **HintDisplay Class**
Formats tutorial messages for CLI:

```python
class HintDisplay:
    """Formats and displays tutorial hints"""

    def show_move_recommendation(self, recommendation: MoveRecommendation):
        """Displays suggested move with highlighting"""

    def show_strategy_lesson(self, lesson: StrategyLesson):
        """Presents strategic concept"""

    def show_move_feedback(self, player_move, analysis):
        """Provides feedback after player chooses"""
```

### 3.2 Data Structures

#### **MoveRecord**
```python
@dataclass
class MoveRecord:
    round_number: int
    turn_number: int
    player_idx: int
    player_name: str
    domino: Domino
    position: str                    # 'left', 'right', 'first'
    board_before: List[Domino]
    board_after: List[Domino]
    hand_value_before: int
    was_double: bool
    was_blocking: bool
    strategy_tags: List[str]         # e.g., ['heavy_first', 'double_early']
```

#### **MoveAnalysis**
```python
@dataclass
class MoveAnalysis:
    domino: Domino
    position: str

    # Scoring
    strategic_score: float           # 0-100, higher is better
    strategic_category: str          # Primary strategy applied

    # Strategic factors
    is_double: bool
    tile_value: int
    blocks_opponent: bool
    helps_ally: bool
    maintains_balance: bool

    # Contextual
    hand_diversity_after: float      # Number variety remaining
    risk_level: str                  # 'low', 'medium', 'high'

    # Explanation
    primary_reason: str              # Main strategic justification
    secondary_factors: List[str]     # Additional considerations
    references_to_history: List[str] # Links to previous moves
```

#### **MoveRecommendation**
```python
@dataclass
class MoveRecommendation:
    best_move: Tuple[Domino, str]
    analysis: MoveAnalysis

    explanation: str                 # Natural language recommendation
    reasoning_steps: List[str]       # Step-by-step logic
    historical_context: List[str]    # References to previous game state

    alternatives: List[MoveAnalysis] # Other good options
    avoid_moves: List[MoveAnalysis]  # Moves to avoid with reasons
```

#### **TileCounter**
```python
class TileCounter:
    """Tracks played tiles for counting strategy"""

    def __init__(self):
        # Each number 0-6 appears exactly 8 times
        self.number_counts = {i: 0 for i in range(7)}
        self.played_tiles = []

    def record_play(self, domino: Domino):
        """Track a played domino"""

    def remaining_count(self, number: int) -> int:
        """How many tiles with this number remain unplayed"""

    def is_number_dead(self, number: int) -> bool:
        """True if all 8 tiles with this number are played"""

    def get_distribution_analysis(self) -> Dict[int, str]:
        """Returns strategic insights about remaining tiles"""
```

---

## 4. Tutorial Mode Levels

### 4.1 Beginner Level

**Focus**: Basic mechanics and simple strategies

**What It Teaches**:
- Play doubles early (visual highlighting + explanation)
- Play high-value tiles first to minimize risk
- Understand how matching works
- Recognize when you have multiple options

**Example Hints**:
```
💡 TUTORIAL TIP - Play Doubles Early
You have [5|5] in your hand. Doubles are harder to play because they only
match one number. Consider playing it now while you still can!

Why? If the board changes and 5s are no longer available, you'll be stuck
with this 10-point tile.
```

### 4.2 Intermediate Level

**Focus**: Strategic thinking and opponent awareness

**What It Teaches**:
- Tile counting basics
- Blocking tactics
- Hand balance management
- Team coordination (keeping numbers for ally)
- Observing opponent passes

**Example Hints**:
```
💡 TUTORIAL TIP - Tile Counting
Looking at the board, 6 tiles with "3" have been played so far. You're
holding [3|5], and only one other tile with "3" remains in play.

Strategic insight: If you play [3|5] on the RIGHT (leaving 5 open), you
control the 3s. This could block opponents who need 3s!

Recommendation: Play [3|5] on RIGHT
```

### 4.3 Advanced Level

**Focus**: Expert tactics and situational play

**What It Teaches**:
- Complex blocking patterns
- Endgame optimization
- Sacrificial plays for team benefit
- Board control strategies
- Psychological aspects (reading opponent patterns)

**Example Hints**:
```
💡 TUTORIAL TIP - Advanced Team Play
Current situation:
- Your ally (Player 2) has passed twice when 4s were available
- They likely have no 4s remaining in their hand
- Your team is leading 145-120 in a 200-point game

Strategy: AVOID playing tiles that create 4s on the board. This prevents
opponents from exploiting your ally's weakness.

Recommendation: Play [6|2] on LEFT (creates 2 and 6 ends, no 4s)
```

---

## 5. Integration with Existing Codebase

### 5.1 Minimal Changes to Core Game

The tutorial system will be **non-invasive**:

```python
class Game:
    def __init__(self):
        # Existing code...
        self.tutorial_engine = None  # Only initialized if tutorial mode on

    def enable_tutorial(self, level: TutorialLevel):
        """Activate tutorial mode"""
        self.tutorial_engine = TutorialEngine(level)
        self.game_historian = GameHistorian()

    def play_turn(self, player):
        # Existing code to display board and hand...

        # NEW: Tutorial hooks (only run if tutorial_engine exists)
        if self.tutorial_engine and player.player_type == PlayerType.HUMAN:
            # Analyze situation before player moves
            recommendation = self.tutorial_engine.suggest_move(
                valid_moves,
                self.get_game_state(),
                self.game_historian
            )

            # Show tutorial hint
            self.tutorial_engine.hint_display.show_recommendation(recommendation)

        # Get move (existing code)
        move = self.get_human_move(player, valid_moves)

        # NEW: Tutorial feedback after move
        if self.tutorial_engine and player.player_type == PlayerType.HUMAN:
            feedback = self.tutorial_engine.analyze_player_move(move, recommendation)
            self.tutorial_engine.hint_display.show_feedback(feedback)

        # Execute move (existing code)
        # ...
```

### 5.2 New Files Structure

```
domino-game-cli/
├── mvp.py                          # Existing game code
├── tutorial_engine.py              # NEW: Main tutorial orchestrator
├── move_analyzer.py                # NEW: Move evaluation logic
├── strategy_advisor.py             # NEW: Strategic recommendations
├── game_historian.py               # NEW: History tracking
├── hint_display.py                 # NEW: Tutorial UI formatting
├── tutorial_strategies.py          # NEW: Strategy definitions & heuristics
└── docs/
    ├── TUTORIAL_MODE_PLAN.md       # This document
    └── STRATEGY_GUIDE.md           # NEW: Player-facing strategy reference
```

### 5.3 Entry Point Modification

```python
def main():
    print("Caribbean Dominoes")
    print("=" * 50)

    # NEW: Tutorial mode selection
    print("\nGame Modes:")
    print("1. Normal Play")
    print("2. Tutorial Mode - Beginner")
    print("3. Tutorial Mode - Intermediate")
    print("4. Tutorial Mode - Advanced")

    choice = input("Select mode (1-4): ").strip()

    game = Game()

    if choice in ['2', '3', '4']:
        level_map = {
            '2': TutorialLevel.BEGINNER,
            '3': TutorialLevel.INTERMEDIATE,
            '4': TutorialLevel.ADVANCED
        }
        game.enable_tutorial(level_map[choice])

    game.play()
```

---

## 6. Tutorial Flow Examples

### 6.1 Example 1: Early Game - Playing Doubles

**Game State**:
- Round 1, Turn 3
- Board: `[6|6] [6|3] [3|1]`
- Board ends: Left=[6], Right=[1]
- Your hand: `[1|2], [2|5], [4|4], [4|6], [5|5], [5|6]`

**Tutorial Output** (Beginner Level):

```
============================================================
Your Turn (Team 1)
============================================================
Board: [6|6] [6|3] [3|1]
Board ends: Left=[6] Right=[1]

Your hand: [1|2]₁, [2|5]₂, [4|4]₃, [4|6]₄, [5|5]₅, [5|6]₆
Hand value: 36 points

Valid moves:
  1. Play [1|2] on right
  2. Play [4|6] on left
  3. Play [5|6] on left

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TUTORIAL RECOMMENDATION - Play Doubles Early
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 BEST MOVE: Play [4|4] on... wait, you can't play [4|4] right now!

❗ STRATEGIC INSIGHT:
You have TWO doubles in your hand: [4|4] and [5|5]
- [4|4] = 8 points (STUCK - neither 4 matches board ends)
- [5|5] = 10 points (STUCK - neither 5 matches board ends)

Neither double can be played this turn because the board ends are [6] and [1].

📚 STRATEGY: "Play Doubles Early"
Doubles are the hardest tiles to play because they only connect to one
number. Right now, you're stuck with 18 points in unplayable doubles!

🎯 RECOMMENDED MOVE: Play [5|6] on LEFT

Why this move?
1. Creates a [5] on the left end, letting you play [5|5] next turn
2. Keeps the [1] on the right for your [1|2] as backup
3. Opens up options for your doubles

Alternative: Play [4|6] on LEFT to enable [4|4] later

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your choice (1-3):
```

**If Player Chooses Recommended Move [5|6]**:

```
✅ EXCELLENT CHOICE!

You played [5|6] on the left, creating this board:
[5|6] [6|6] [6|3] [3|1]

Board ends are now: Left=[5] Right=[1]

Next turn strategy: Watch for opportunities to play [5|5]. You've set
yourself up perfectly!
```

### 6.2 Example 2: Mid-Game - Tile Counting & Blocking

**Game State**:
- Round 1, Turn 8
- Board: `[6|6] [6|3] [3|1] [1|5] [5|2] [2|4]`
- Board ends: Left=[6], Right=[4]
- Your hand: `[4|3], [4|5]`
- Opponent 1 passed last turn when 6 was available
- 6 tiles with "6" have been played

**Tutorial Output** (Intermediate Level):

```
============================================================
Your Turn (Team 1)
============================================================
Board: [6|6] [6|3] [3|1] [1|5] [5|2] [2|4]
Board ends: Left=[6] Right=[4]

Your hand: [4|3], [4|5]
Hand value: 12 points

Valid moves:
  1. Play [4|3] on right
  2. Play [4|5] on right

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TUTORIAL RECOMMENDATION - Blocking Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧮 TILE COUNT ANALYSIS:
Looking at the board, I count:
- Tiles with 6: [6|6]×1 + [6|3]×1 = 2 tiles played so far
- Tiles with 4: [2|4]×1 = 1 tile played so far

🔍 OPPONENT BEHAVIOR:
Opponent 1 (Team 2) PASSED on Turn 6 when the left end was [6].
This strongly suggests they have NO tiles with 6.

🎯 RECOMMENDED MOVE: Play [4|3] on RIGHT

Why this is strategically superior:
1. Creates board ends [6] and [3]
2. Opponent 1 can't play on [6] (they passed before!)
3. If Opponent 1 also lacks 3s, they'll pass again
4. This gives control back to your team sooner

Alternative move: Play [4|5] on RIGHT
- Creates board ends [6] and [5]
- Okay, but less targeted blocking
- Opponent might have 5s

📊 STRATEGIC PRINCIPLE: "Block Using Known Information"
When opponents pass, remember what numbers they couldn't play. Use this
intelligence to create board ends they can't match, forcing more passes
and giving your team more turns!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your choice (1-2):
```

**If Player Chooses [4|3] (recommended)**:

```
✅ SMART BLOCKING MOVE!

You played [4|3] on the right: [6|6] [6|3] [3|1] [1|5] [5|2] [2|4] [4|3]
Board ends: Left=[6] Right=[3]

📊 Result:
[Turn 9] Opponent 1 (Team 2) PASSED! (Can't play on 6 or 3)

Perfect! Your blocking strategy worked. By remembering their Turn 6 pass,
you correctly predicted they'd be stuck. Your team maintains control!
```

### 6.3 Example 3: Endgame - Sacrificial Team Play

**Game State**:
- Round 3, Turn 20
- Board: Long chain with ends [2] and [5]
- Your hand: `[2|6]`
- Your ally's hand: 2 tiles remaining (went from 4 to 2 in 2 turns)
- Your ally played [5|4] last turn
- Your team is behind 165-180 in 200-point game

**Tutorial Output** (Advanced Level):

```
============================================================
Your Turn (Team 1)
============================================================
Board ends: Left=[2] Right=[5]

Your hand: [2|6]
Hand value: 8 points

Valid move:
  1. Play [2|6] on left

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TUTORIAL RECOMMENDATION - Advanced Team Coordination
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 CRITICAL SITUATION ANALYSIS:

Score Status:
- Your team (Team 1): 165 points
- Opponent team (Team 2): 180 points
- BEHIND by 15 points, need 35 to win

Ally Status (Player 2):
- Turn 18: Played [3|5] (down to 3 tiles)
- Turn 19: Played [5|4] (down to 2 tiles)
- Current: Has only 2 tiles left!
- Just played [5|4], connecting to 5 and leaving 4

Team Strategy Insight:
Your ally is racing to go out! If they empty their hand, your team scores
ALL remaining points from opponents' hands (likely 30-50 points).

🎯 CRITICAL DECISION: Where to play [2|6]?

Option 1: Play [2|6] on LEFT (creating ends [6] and [5])
- Blocks opponents from using 2
- Board ends: [6] and [5]
- Your ally just played [5|4], suggesting they might have tiles with 4, 5, or 6
- SUPPORTS ally's potential tiles!

Option 2: Play [2|6] on RIGHT (creating ends [2] and [6])
- Keeps 5 available on right
- Ally played [5|4] last turn—if they have another tile with 5, this helps
- But less blocking power

📊 RECOMMENDED: Play [2|6] on LEFT (Option 1)

Strategic Reasoning:
1. Your ally reduced their hand by 2 tiles recently (aggressive pace)
2. They connected through 5→4, likely holding more mid-range numbers
3. Creating [6] and [5] ends maximizes ally options
4. You're behind—need ally to go out this round to score big
5. Your 8-point tile is worth sacrificing to enable ally's victory

⚠️ ADVANCED CONCEPT: "Sacrificial Team Play"
When your ally is close to going out and your team needs points, prioritize
moves that help THEM play, even if it's not your personal best move. A team
win is better than individual optimization!

Historical context:
- Turn 18: Ally played aggressively
- Turn 19: Ally continued aggressive pace
- Turn 20 (now): Support their momentum!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your choice: [Press Enter to play [2|6] on LEFT]
```

---

## 7. Strategic Scoring System

The `MoveAnalyzer` will score moves using this weighted system:

### Scoring Formula

```python
def calculate_strategic_score(move: Move, game_state: GameState) -> float:
    """Returns 0-100 score for move quality"""
    score = 50.0  # Base score

    # Factor 1: Tile value optimization (0-20 points)
    # Play high tiles early, low tiles late
    if game_state.turn_phase == 'early':
        score += (move.domino.value() / 12) * 20  # Higher is better
    elif game_state.turn_phase == 'late':
        score += ((12 - move.domino.value()) / 12) * 20  # Lower is better

    # Factor 2: Double priority (0-15 points)
    if move.domino.is_double():
        doubles_in_hand = count_doubles(game_state.player_hand)
        score += min(doubles_in_hand * 5, 15)

    # Factor 3: Hand balance (0-15 points)
    diversity_before = calculate_diversity(game_state.player_hand)
    diversity_after = calculate_diversity_after_move(game_state.player_hand, move)
    if diversity_after >= diversity_before:
        score += 15
    elif diversity_after < diversity_before - 1:
        score -= 10

    # Factor 4: Blocking potential (0-20 points)
    if move.blocks_opponent(game_state.opponent_patterns):
        score += 20

    # Factor 5: Team coordination (0-15 points)
    if move.helps_ally(game_state.ally_pattern):
        score += 15

    # Factor 6: Tile counting insights (0-15 points)
    if move.leverages_tile_count(game_state.tile_counter):
        score += 15

    return min(max(score, 0), 100)  # Clamp to 0-100
```

### Strategic Categories

Each move is tagged with primary strategies:

```python
STRATEGIES = {
    'double_early': "Playing doubles early to avoid getting stuck",
    'heavy_first': "Playing high-value tiles to minimize penalty risk",
    'balanced_hand': "Maintaining variety of numbers for flexibility",
    'blocking': "Creating board ends opponent can't match",
    'team_support': "Helping ally by keeping their numbers available",
    'tile_counting': "Using knowledge of played tiles",
    'board_control': "Creating favorable board ends for future",
    'defensive': "Keeping low tiles for endgame",
    'aggressive_out': "Racing to empty hand"
}
```

---

## 8. Historical Context System

### 8.1 Reference Types

The tutorial will reference previous game events in explanations:

**Type 1: Direct Previous Move**
```
"Last turn, Opponent 1 passed when [3] was available..."
```

**Type 2: Pattern Recognition**
```
"Opponent 2 has now passed twice on [6]s over the last 5 turns, suggesting
they have no tiles with 6."
```

**Type 3: Board Evolution**
```
"The board started with [6|6], then you created a [3] end on Turn 2 by
playing [6|3]. Now, 6 turns later, that [3] is still causing problems
because 4 tiles with 3 have been played."
```

**Type 4: Team Momentum**
```
"Your ally has played 3 tiles in the last 4 turns while opponents passed
twice. Maintain this pressure!"
```

### 8.2 Implementation

```python
class GameHistorian:
    def generate_context(self, current_move, game_state) -> List[str]:
        """Creates relevant historical references"""
        context = []

        # Check for recent passes on current board numbers
        recent_passes = self.find_recent_passes(
            numbers=[game_state.board.left_value(), game_state.board.right_value()],
            turns_back=5
        )
        for pass_event in recent_passes:
            context.append(
                f"Turn {pass_event.turn}: {pass_event.player} passed when "
                f"[{pass_event.number}] was available"
            )

        # Check for tile count milestones
        for number in [current_move.domino.left, current_move.domino.right]:
            remaining = game_state.tile_counter.remaining_count(number)
            if remaining <= 2:
                context.append(
                    f"Only {remaining} tiles with [{number}] remain unplayed!"
                )

        # Check for team dynamics
        if game_state.ally_just_played():
            ally_move = self.get_last_move(game_state.ally_idx)
            context.append(
                f"Your ally played [{ally_move.domino}] last turn, creating "
                f"ends [{game_state.board.left_value()}] and "
                f"[{game_state.board.right_value()}]"
            )

        return context
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Core infrastructure without AI

**Deliverables**:
- `GameHistorian` class - tracks all moves and board states
- `TileCounter` class - counts played tiles
- `MoveRecord` and data structures
- Integration hooks in `Game.play_turn()`
- Basic test suite

**Acceptance Criteria**:
- Game history accurately recorded for all moves
- Tile counter correctly tracks 8 instances per number
- No impact on normal game mode

### Phase 2: Move Analysis (Week 3-4)
**Goal**: Evaluate move quality

**Deliverables**:
- `MoveAnalyzer` class with scoring algorithm
- Strategic heuristics implementation
- `MoveAnalysis` data structure with scores
- Unit tests for 20+ move scenarios

**Acceptance Criteria**:
- Analyzer correctly identifies doubles
- High-value tiles scored appropriately for early game
- Blocking moves detected and scored higher
- All 9 core strategies have scoring logic

### Phase 3: Strategy Advisor (Week 5-6)
**Goal**: Generate recommendations

**Deliverables**:
- `StrategyAdvisor` class
- Natural language explanation generator
- Historical context integration
- 50+ canned explanation templates

**Acceptance Criteria**:
- Top 3 moves identified each turn
- Explanations reference previous game state
- Strategic reasoning connects to theory
- Works for all game phases (early/mid/late)

### Phase 4: Display & UI (Week 7)
**Goal**: Present tutorial information

**Deliverables**:
- `HintDisplay` class with CLI formatting
- Color/highlighting support (if terminal supports)
- Move recommendation display template
- Post-move feedback system

**Acceptance Criteria**:
- Hints clearly formatted and readable
- Not overwhelming (concise, scannable)
- Optional verbosity settings
- Works on 80-column terminals

### Phase 5: Tutorial Levels (Week 8)
**Goal**: Difficulty progression

**Deliverables**:
- `TutorialLevel` enum and configuration
- Beginner level (basic strategies only)
- Intermediate level (adds tile counting)
- Advanced level (full strategic depth)
- Mode selection in main menu

**Acceptance Criteria**:
- Beginner shows 2-3 strategies max
- Intermediate introduces counting
- Advanced includes team coordination
- Players can switch levels mid-game

### Phase 6: Polish & Testing (Week 9-10)
**Goal**: Production-ready quality

**Deliverables**:
- Comprehensive integration tests
- Play-testing with real users
- Bug fixes and edge cases
- Performance optimization (ensure no lag)
- Documentation for players

**Acceptance Criteria**:
- 100+ turn scenarios tested
- No crashes or infinite loops
- Tutorial explanations verified accurate
- User feedback incorporated

---

## 10. Success Metrics

### Quantitative Metrics
- **Move Quality Improvement**: Player's average move score increases by 20+ points after 5 tutorial games
- **Strategy Adoption**: Players use 4+ taught strategies independently by game 5
- **Completion Rate**: 80%+ of players complete at least 3 tutorial games
- **Performance**: Tutorial analysis adds <500ms to turn time

### Qualitative Metrics
- **Clarity**: 90%+ of players understand why recommended moves are better
- **Engagement**: Players report tutorial enhances learning (survey)
- **Progression**: Players graduate from Beginner to Intermediate naturally

### Testing Scenarios
1. **Beginner with no domino experience**: Should learn basic matching and double priority
2. **Intermediate player**: Should learn tile counting and blocking
3. **Advanced player using tutorial**: Should discover team coordination tactics
4. **Player ignoring tutorial suggestions**: Should see feedback that explains suboptimal choices

---

## 11. Future Enhancements

### Version 2.0 Features
- **Replay Mode**: Review past games with tutorial analysis overlaid
- **Strategy Statistics**: Track which strategies player uses most/least
- **Custom Challenges**: Scenario-based learning (e.g., "Practice blocking with this hand")
- **Adaptive Difficulty**: Tutorial adjusts based on player's move quality
- **Multiplayer Tutorial**: Teach team communication in 2v2

### Version 3.0 Features
- **AI Difficulty Tiers**: Teach against progressively smarter AI opponents
- **Strategy Sandbox**: "What if?" mode to explore alternate moves
- **Achievement System**: Unlock badges for mastering strategies
- **Video Explanations**: Animated board states showing strategy effects

---

## 12. Technical Considerations

### Performance
- Tutorial analysis must not slow down gameplay
- Target: <300ms for move analysis
- Cache repeated calculations (e.g., tile counts)

### Memory
- Store only last 50 moves in detailed history
- Summarize earlier moves for context
- Keep memory footprint under 10MB

### Compatibility
- Must work on standard 80x24 terminals
- Gracefully degrade on limited color support
- No external dependencies beyond Python stdlib

### Testing Strategy
- Unit tests for each analyzer component
- Integration tests for full tutorial flow
- Golden file tests for explanation text
- Performance benchmarks for analysis speed

---

## 13. Open Questions for Discussion

1. **Verbosity Control**: Should players adjust how detailed hints are?
2. **Timing**: Show hint before or after player starts thinking?
3. **Mistakes**: Should tutorial intervene if player makes bad move?
4. **Skip Option**: Allow players to hide hints for specific turns?
5. **Persistence**: Save tutorial progress across game sessions?

---

## Appendix A: Example Full Game Flow

See separate document `TUTORIAL_EXAMPLE_GAME.md` for a complete annotated game showing all tutorial interactions.

---

## Appendix B: Strategy Reference Card

Quick reference for developers implementing scoring:

| Strategy | Early Game | Mid Game | Late Game | Score Weight |
|----------|-----------|----------|-----------|-------------|
| Play Doubles | High | Medium | Low | 15 pts |
| Play Heavy | High | Medium | Low | 20 pts |
| Balance Hand | Medium | High | Medium | 15 pts |
| Tile Counting | Low | High | High | 15 pts |
| Blocking | Low | Medium | High | 20 pts |
| Team Support | Medium | High | High | 15 pts |

---

## Summary

This tutorial mode will transform the Caribbean dominoes game into an educational tool that teaches players proven winning strategies through contextual, real-time guidance. By analyzing move quality, referencing game history, and explaining strategic reasoning, players will develop deep understanding of dominoes tactics and improve their gameplay naturally.

**Next Steps**:
1. Review and approve this plan
2. Begin Phase 1 implementation (Foundation)
3. Create test dataset of strategic scenarios
4. Start user testing with Beginner level

**Estimated Timeline**: 10 weeks to full production-ready tutorial mode
**Estimated Effort**: 150-200 development hours
