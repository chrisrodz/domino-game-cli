export { Board, type End, type Ends } from './board.ts';
export {
  MAX_TARGET,
  MODES,
  Match,
  parseMode,
  roundResult,
  type MatchOptions,
  type MatchRecord,
  type Mode,
  type Phase,
  type RoundLog,
  type RoundRecord,
  type Turn,
  type TurnRecord,
} from './match.ts';
export { seededRandom, shuffleWith, type Shuffle } from './random.ts';
export { audit } from './referee.ts';
export {
  HAND_SIZE,
  OPENING_TILE,
  RuleError,
  SEATS,
  isBlocked,
  legalMoves,
  nextSeat,
  pips,
  scoreRound,
  teamOf,
  type Move,
  type RoundOutcome,
  type Team,
} from './rules.ts';
export { MAX_ACTIONS, playOut, simulate, type SimulationOptions, type SimulationReport } from './simulate.ts';
export { simpleStrategy, type CpuStrategy } from './strategy.ts';
export {
  MAX_PIPS,
  createDeck,
  flip,
  formatTile,
  hasValue,
  isDouble,
  parseTileId,
  pipsOf,
  sameTile,
  tile,
  tileId,
  type Tile,
} from './tile.ts';
