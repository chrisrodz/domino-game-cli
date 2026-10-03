# Jev decision design

Simple uses the existing local greedy strategy. Medium and Hard use TypeSafe Jev for narrow tactical judgments,
then combine those judgments in Python. Each CPU seat selects its difficulty independently.

## Information boundary

Both Jev levels receive only the acting player's hand, visible board, public tile counts, scores, and engine rules.
Medium has no turn chronology, remembered passes, previous round results, or deductions from history.
Hard receives the complete public history up to the current turn. Pass exclusions and suit signals use the current deal
only. Public blocked-round pip totals become available after scoring reveals them; other hands remain private.

The unseen pool is the double-six set minus visible tiles and the acting player's tiles. Python derives possible tile
owners and per-seat pip bounds from that pool, public counts, and, for Hard, public passes. These are feasible alternatives,
not the actual hands or ownership probabilities. Redistributing hidden tiles without changing public facts leaves the
request unchanged.

## Decision flow

1. Enumerate legal tile/side moves and compute their resulting ends and remaining hand.
2. Compute suit counts, immediate playable tiles, own-hand connections, vulnerable doubles, and possible blocking outcomes.
3. Take an immediate finish or proven winning block. Hard also takes a proven partner finish after the next opponent must
   pass. Exclude proven losing blocks and guaranteed next-opponent finishes when another move remains.
4. Ask all remaining independent questions in one System One request.
5. Validate answers, normalize scores, apply uncertainty and public-signal gates, then combine with policy weights.
6. Choose a legal move; break equal totals deterministically using remaining pips, immediate mobility, tile, and side.

Questions in the same request cannot consume each other's answers. Every instruction names its candidate's state path.
Jev does no arithmetic, hidden-hand reconstruction, or imagined search through future turns. Connections describe the
current hand structure; other seats may change the ends before the actor plays again.

## Tactical questions

Each Score has five concrete descriptions, from a harmful outcome through neutral to a useful outcome. The levels describe
one dimension; they are not generic "bad" through "excellent" labels.

| Dimension | Question | Level |
|-----------|----------|-------|
| Continuation | Does this move preserve useful connections through the remaining hand? | Medium, Hard |
| Suit control | Does it retain access to suits the hand can sustain and spare connectors? | Medium, Hard |
| Doubles | Does it release vulnerable doubles or preserve access to them? | Medium, Hard |
| Partner | Are the resulting ends compatible with demonstrated partner suit signals? | Hard |
| Pressure | Does it cut the next opponent's supported routes? | Hard |
| Blocking | Is steering toward closure useful under the supplied pip bounds and exit pressure? | Hard, when closure is plausible |

Pip relief is an exact computed component. Permanent double stranding, forced passes, possible immediate exits, and pip
bounds are supplied as computed facts rather than extra questions. A known inability to play applies immediately only to
the next seat; a later seat may encounter different ends.

Hard adds Noul questions about specific suits promoted by the partner or next opponent. A compulsory opening, last-tile
play, or choice without demonstrated alternatives does not establish preference. Later public plays can prove that an
alternative was in that player's hand during an earlier turn, because this game has no drawing. A signal affects a move
only when its suit is among the current or resulting ends and remains possible for that seat to hold.

## Combining answers

A normalized Score is `score / 4`. Its semantic contribution becomes
`0.5 + (normalized_score - 0.5) * confidence`. Confidence measures answer concentration, not the chance of winning.
Public suit signals additionally gate partner and pressure judgments. An unsubstantiated signal leaves that component
neutral. Exact deductions are never discounted by model confidence.

Base weights:

| Component | Medium | Hard |
|-----------|--------|------|
| Continuation | 0.42 | 0.25 |
| Suit control | 0.25 | 0.15 |
| Doubles | 0.18 | 0.10 |
| Pip relief | 0.15 | 0.10 |
| Partner | - | 0.15 |
| Pressure | - | 0.15 |
| Blocking | - | 0.10 |

Hard uses defensive priorities when the next opponent has at most two tiles, otherwise partner support when the partner
has at most two. A plausible favorable closure raises blocking priority. Match-ending pip exposure increases pip relief.
Weights are normalized after each adjustment. These are explicit heuristics, not trained probabilities or a guarantee
that Hard wins more often.

## Rules and reliability

Judgments follow this CLI's rules: four players, seven tiles each, no drawing, first empty hand wins; a block is decided
by the lowest individual hand, ties favor the last-playing team, and blocked points include all remaining hands.
Later rounds currently start at seat 0. No capicu, opening-pass, double-out, or regional bonus is assumed.

One request evaluates all tactical questions. Forced moves and proven finishes bypass the network. The official SDK uses
two-second HTTP timeouts with no retries. Timeout, service failure, or missing/invalid judgments visibly fall back to Simple
for that turn. Credential/request errors stop with an actionable message. Validation allows accumulated independent
two-decimal rounding of returned score distributions, while rejecting nonfinite values, invalid ranges, and inconsistent
answers outside that rounding tolerance.

Hard retains complete public history as requested. Very long matches may exceed the service context limit; no history is
silently dropped. The SDK's model default can be overridden with `TYPESAFE_DEFAULT_MODEL`.

## Validation and comparison

Tests cover legal projection, hidden-hand redistribution, history isolation/reset, exhaustive allocation checks for pip
bounds, stranded doubles, forced passes, proven outcomes, signal gating, priority changes, answer validation, fallback,
and complete rounds in both displays.

With `TYPESAFE_API_KEY` already in the environment:

```bash
uv run python -m scripts.benchmark_jev --seeds 17 42 --levels medium hard
```

This plays tactical Jev against the original broad Choice prompt on the same shuffled deals, rotating every hand through
all four seats. Both teams use the selected difficulty's information boundary. All four seats are automated for this
comparison. The baseline receives its original state and options, without the new computed tactical features.
The benchmark reports round wins, points, API calls, input tokens, decision latency including observation construction,
and exact-code decisions. Service failures stop the comparison; there is no hidden fallback. SDK/model revisions can
change results even with fixed deals. A small sample checks integration and cost/latency; a strength claim needs many
more independent deals and separate evaluation after tuning.

### Initial live sample

On Jev 1.13.0, seeds 17 and 42 rotated through all four seats completed 16 rounds with no fallback:

| Difficulty | Tactical wins | Tactical / baseline points | Tactical / baseline calls | Tactical / baseline input tokens | Tactical / baseline mean decision time |
|------------|---------------|----------------------------|---------------------------|---------------------------------|----------------------------------------|
| Medium | 5 of 8 | 158 / 80 | 54 / 61 | 258,833 / 65,820 | 0.223 / 0.203 seconds |
| Hard | 6 of 8 | 148 / 43 | 59 / 61 | 507,520 / 112,872 | 0.265 / 0.212 seconds |

The tactical design used roughly four times the input tokens, with similar subsecond decision latency in this sample.
These two underlying deals do not establish a win-rate advantage or that Hard is stronger than Medium. They expose the
cost tradeoff and provide a reproducible starting point for a larger, independent evaluation.

## Design references

- [TypeSafe composite scoring](https://docs.typesafe.ai/patterns/composite-scoring): independent dimensions, weights in code.
- [TypeSafe fan-out](https://docs.typesafe.ai/patterns/fan-out): independent questions in one request.
- [TypeSafe confidence](https://docs.typesafe.ai/confidence): interpreting answer uncertainty.
- [TypeSafe Score](https://docs.typesafe.ai/primitives/score): concrete ordered rubrics and score normalization.
- [Partnership dominoes](https://www.pagat.com/domino/line/partnership.html): partnership tactics and regional rule variations.
- [Dominican strategy guide](https://fichaflow.com/es/learn/guide/): suit repetition, opponent pressure, and blocking heuristics.

Regional advice informs the questions; the engine's supplied rule profile determines which tactics and counts apply.
