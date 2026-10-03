const cell = (text, tag = "td") => {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
};

export function renderScorebook(state) {
  const rounds = state.rounds ?? [];
  const body = document.querySelector("#scorebook-rows");
  body.replaceChildren(
    ...rounds.map((round) => {
      const row = document.createElement("tr");
      const number = cell(String(round.round).padStart(2, "0"), "th");
      number.scope = "row";
      row.append(number, cell(round.blocked ? "Trancado" : "Domin\u00f3"));
      [0, 1].forEach((team) => {
        const score = cell(round.team === team ? `+${round.points}` : "-");
        if (round.team === team) score.className = "hand-points";
        const total = document.createElement("span");
        total.className = "hand-total";
        total.textContent = `${round.scores[team]} total`;
        score.append(total);
        row.append(score);
      });
      row.title = `${round.winner ? `${round.winner} cleared their hand.` : "The lowest hand won."} Remaining pips: ${round.unplayed.map((hand) => `${hand.name} ${hand.value}`).join(", ")}.`;
      return row;
    }),
  );
  document.querySelector("#scorebook-empty").hidden = rounds.length > 0;
  document.querySelector("#scorebook-table").hidden = !rounds.length;
  document.querySelector("#book-us").textContent = state.scores[0];
  document.querySelector("#book-them").textContent = state.scores[1];
  document.querySelector("#book-target").textContent =
    state.mode === "single_round" ? "One round" : `First to ${state.target}`;
  document.querySelector("#book-caption").textContent = rounds.length
    ? `${rounds.length} ${rounds.length === 1 ? "hand" : "hands"} played. Every point, accounted for.`
    : "The first hand is still on the table.";
}
