// Execute production functions with small deterministic inputs, without a browser.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = readFileSync('site/assets/app.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, name);
  return source.slice(start, source.indexOf('\n}\n', start) + 2);
}
const state = {
  todayDate: '30d', q: '', source: '', kind: '', category: '', organization: '', event: '',
  data: { latest_date: '2026-09-06', facets: { dates: ['2026-09-06'] } },
};
const observation = (date, id = date) => ({
  snapshot_date: date, observation_kind: 'evidence', source: 'GitHub', source_id: id,
  title: 'agent benchmark', summary: '', categories: [],
});
let observations = [observation('2026-09-07'), observation('2026-09-06'), observation('2026-08-08', 'repeated'), observation('2026-08-09', 'repeated'), observation('2026-08-07'), observation('2026-07-09'), observation('2026-07-08')];
const dateNames = ['todayDateRange', 'todayIsMultiDate', 'validTodayDate', 'filteredObservations', 'observationRecordKey', 'latestObservationsByRecord'];
const dates = new Function('state', 'allObservations', `${source.match(/const TODAY_WINDOWS = .*;/)[0]}\n${dateNames.map(fn).join('\n')}\nreturn {${dateNames.join(',')}};`)(state, () => observations);
assert.deepEqual(dates.todayDateRange(), {start:'2026-08-08',end:'2026-09-06'});
assert.equal(dates.validTodayDate(), true);
assert.deepEqual(dates.filteredObservations().map(r=>r.snapshot_date), ['2026-09-06','2026-08-09']);
state.todayDate = '60d';
assert.deepEqual(dates.todayDateRange(), {start:'2026-07-09',end:'2026-09-06'});
assert.equal(dates.filteredObservations().length, 4);
state.todayDate = 'all';
assert.equal(dates.filteredObservations().length, 6);
state.todayDate = '2026-08-08';
assert.equal(dates.filteredObservations()[0].snapshot_date, '2026-08-08');
state.todayDate = '30d';
state.q = 'absent';
assert.equal(dates.filteredObservations().length, 0);
state.q = 'agent';
state.source = 'github';
assert.equal(dates.filteredObservations().length, 2);
state.data.latest_date = '2024-03-01';
assert.deepEqual(dates.todayDateRange(), {start:'2024-02-01',end:'2024-03-01'});

const summary = (display_max, numeric_count=1) => ({display_max,numeric_count,display_multiplier:1});
state.data.model_card_leaderboard = {entries:[{benchmark_id:'curated',name:'Curated'}]};
state.data.benchmark_score_progression = {benchmarks:{curated:{score_summary:summary(60,2)}}};
state.benchmarkIndex = [
  {slug:'external',name:'External',source:'llm_stats',score_summary:summary(60,9)},
  {slug:'over70',name:'Over70',source:'artificial_analysis',score_summary:summary(70,20)},
  {slug:'at100',name:'At100',source:'llm_stats',score_summary:summary(100,30)},
  {slug:'missing',name:'Missing',source:'llm_stats',score_summary:summary(null,0)},
];
state.lscore = 70;
const scoreNames = ['scoreRecord','matchesScoreFilter','scoreBrowseRows','frontierDefaultEntry','externalDisplayFactor'];
const scores = new Function('state', `${scoreNames.map(fn).join('\n')}\nreturn {${scoreNames.join(',')}};`)(state);
assert.deepEqual(scores.scoreBrowseRows().map(r=>[r.id,r.rank]), [['external',1],['curated',2]]);
assert.equal(scores.frontierDefaultEntry(state.data.model_card_leaderboard).id,'external');
assert.equal(scores.matchesScoreFilter(summary(69.999)),true);
assert.equal(scores.matchesScoreFilter(summary(70)),false);
assert.equal(scores.matchesScoreFilter(summary(60,0)),false);
state.lscore=100;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['at100','over70','external','curated']);
state.lscore=90;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['over70','external','curated']);
// An intermediate step the old three-option filter could not express.
state.lscore=40;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), []);
state.lscore=70;
state.benchmarkIndex=null;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['curated']);
assert.equal(scores.externalDisplayFactor({score_summary:{display_multiplier:100}}),100);
assert.equal(scores.externalDisplayFactor({score_summary:{display_multiplier:1}}),1);
const cutoff = new Function(`${fn('scoreCutoff')}\nreturn scoreCutoff;`)();
assert.equal(cutoff('40'), 40);
assert.equal(cutoff('100'), 100);
assert.equal(cutoff(null), 70, 'a missing cutoff falls back to the default');
assert.equal(cutoff('under70'), 70, 'a stale token from an old link falls back');
assert.equal(cutoff('5'), 70, 'below the slider minimum falls back');
assert.equal(cutoff('999'), 70, 'above the slider maximum falls back');
assert.equal(cutoff('44'), 40, 'an off-step value snaps to the nearest step');

// --- Score histogram ---------------------------------------------------------
const histNames = ['monthIndexOf','monthFromIndex','scoreBandOf','isoDepth','scoreHistogramCells'];
const histConsts = source.match(/const HISTOGRAM_BANDS = \d+;/)[0] + '\n'
  + source.match(/const HISTOGRAM_WINDOW_MONTHS = \d+;/)[0];
const hist = new Function(`${histConsts}\n${histNames.map(fn).join('\n')}\nreturn {${histNames.join(',')}};`)();

// High bands sit at the back so the heavy rows cannot bury the sparse ones.
// Painter's ordering depends on this; a flipped mapping would silently hide bars.
assert.equal(hist.isoDepth(9), 0);
assert.equal(hist.isoDepth(0), 9);

assert.equal(hist.scoreBandOf(69.9), 6);
assert.equal(hist.scoreBandOf(70), 7);
assert.equal(hist.scoreBandOf(0), 0);
assert.equal(hist.scoreBandOf(100), 9, 'a 100 clamps into the top band rather than a tenth one');

assert.equal(hist.monthIndexOf('2026-01') - hist.monthIndexOf('2025-12'), 1, 'months step across a year boundary');
assert.equal(hist.monthFromIndex(hist.monthIndexOf('2024-03')), '2024-03');

const track = (unit, rows) => ({unit, name: unit, observations: rows.map(([reported_at, value]) => ({reported_at, value}))});
const bench = {
  pct: track('percent', [['2026-08-01', 65], ['2026-08-20', 62], ['2026-07-01', 12], ['2025-01-01', 40]]),
  elo: track('elo', [['2026-08-02', 1400]]),
  usd: track('usd', [['2026-08-03', 5000]]),
};
const all = hist.scoreHistogramCells(bench, 100);
// A 1400 Elo would clamp into "90-99" and sit beside a percentage as though the
// two measured the same thing, so non-percent units never enter the figure.
assert.equal(all.total, 3, 'only in-window percent scores are plotted');
assert.equal(all.excluded, 1, 'the 2025 score is counted as outside the window');
assert.equal(all.months.length, 12);
assert.equal(all.months[all.months.length - 1], '2026-08');
assert.equal(all.months[0], '2025-09');

// The spine keeps every calendar month, so a gap stays a gap.
assert.ok(all.months.includes('2025-11'), 'empty months remain on the axis');

const under = hist.scoreHistogramCells(bench, 60);
assert.equal(under.total, 1, 'the cutoff hides whole bands, not whole benchmarks');
assert.ok([...under.cells.values()].every((cell) => cell.band * 10 < 60));

const aug = [...all.cells.values()].find((cell) => cell.band === 6);
assert.equal(aug.count, 2, 'two August scores share the 60-69 band');
assert.equal(aug.tracks.size, 1);

assert.equal(hist.scoreHistogramCells({}, 100).cells.size, 0, 'an empty corpus yields no cells');

// Painter's algorithm: far cells first. Verified against the three neighbours
// that can occlude a cell.
const order = [...all.cells.values()]
  .sort((a, b) => (a.slot + hist.isoDepth(a.band)) - (b.slot + hist.isoDepth(b.band)) || a.slot - b.slot);
const key = (c) => `${c.slot}|${hist.isoDepth(c.band)}`;
const at = new Map(order.map((c, i) => [key(c), i]));
order.forEach((cell) => {
  const m = cell.slot;
  const d = hist.isoDepth(cell.band);
  [[1, 0], [0, 1], [1, 1]].forEach(([dm, dd]) => {
    const front = at.get(`${m + dm}|${d + dd}`);
    if (front !== undefined) {
      assert.ok(front > at.get(key(cell)), 'a nearer cell must be painted after the one behind it');
    }
  });
});

console.log('Date windows, deduplication, cutoff boundaries, source-neutral ranking, shared scale, and histogram cells passed.');
