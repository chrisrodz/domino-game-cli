// Replays every deal the Python engine recorded and requires identical turns, outcomes, and scores.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { Match, audit, parseTileId, playOut, roundResult, type MatchRecord, type Shuffle } from '../src/index.ts';

interface Fixture {
  matches: { seed: number; record: MatchRecord; outcomes: Record<string, unknown>[] }[];
}

const fixture = JSON.parse(
  readFileSync(new URL('./fixtures/conformance.json', import.meta.url), 'utf8')
) as Fixture;

function replayDeals(record: MatchRecord): Shuffle {
  const deals = record.rounds.map((round) => round.deal.flat().map(parseTileId));
  return () => {
    const deal = deals.shift();
    if (!deal) throw new Error('The engine dealt more rounds than Python recorded.');
    return deal;
  };
}

test('the fixture covers a meaningful number of matches', () => {
  assert.ok(fixture.matches.length >= 20);
});

for (const { seed, record, outcomes } of fixture.matches) {
  test(`${record.mode} to ${record.target}, Python seed ${seed}: CPU play matches Python turn for turn`, () => {
    const match = playOut(new Match({ target: record.target, mode: record.mode, shuffle: replayDeals(record) }));
    assert.deepEqual(match.toRecord(), record);
    assert.deepEqual(
      match.rounds.map((log) => ({ ...roundResult(log), scores: log.scores })),
      outcomes
    );
    assert.deepEqual(audit(match), []);
  });

  test(`${record.mode} to ${record.target}, Python seed ${seed}: fromRecord restores the finished match`, () => {
    const restored = Match.fromRecord(record);
    assert.equal(restored.phase, 'match_over');
    assert.deepEqual(restored.toRecord(), record);
    assert.deepEqual(restored.scores, outcomes.at(-1)?.scores);
  });
}
