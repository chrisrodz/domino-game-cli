import { layoutBoard } from "./domino-layout.js";

export function previewPlacement(state, { tileId, position, spec }) {
  if (!state.moves.some((move) => move.tile === tileId && move.position === position)) return null;
  const tile = state.players[0].hand.find((tile) => tile.id === tileId);
  if (!tile) return null;
  const flip =
    position === "left"
      ? tile.right !== state.ends.left
      : position === "right"
        ? tile.left !== state.ends.right
        : false;
  const oriented = flip ? { ...tile, left: tile.right, right: tile.left } : tile;
  const board = position === "left" ? [oriented, ...state.board] : [...state.board, oriented];
  return {
    board,
    layout: layoutBoard(board, { spec, opening: state.opening ?? tileId }),
    tileId,
    position,
  };
}
