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
const histNames = ['histogramDomain','scoreHistogramRows'];
const histConsts = source.match(/const HISTOGRAM_MIN_REPORTS = \d+;/)[0] + '\n'
  + source.match(/const HISTOGRAM_DOMAINS = \{[\s\S]*?\n\};/)[0];
const hist = new Function(`${histConsts}\n${histNames.map(fn).join('\n')}\nreturn {${histNames.join(',')}};`)();

assert.equal(hist.histogramDomain('coding_agent'), 'Coding');
assert.equal(hist.histogramDomain('reasoning'), 'Math');
assert.equal(hist.histogramDomain(undefined), 'Other', 'an unmapped domain still gets a colour');

const obs = (n, at, value) => Array.from({length: n}, (_, i) => ({reported_at: at, value: value - i}));
const bench = {
  kept: {unit: 'percent', score_summary: {numeric_count: 4, display_max: 60}, organization_count: 2,
    observations: obs(4, '2026-02-01', 60)},
  thin: {unit: 'percent', score_summary: {numeric_count: 2, display_max: 55},
    observations: obs(2, '2026-02-01', 55)},
  elo: {unit: 'elo', score_summary: {numeric_count: 9, display_max: 3206},
    observations: obs(9, '2026-02-01', 3206)},
};
const entries = [{benchmark_id: 'kept', name: 'Kept', domain: 'math'}];

const model = hist.scoreHistogramRows(bench, entries, 100);
// A 3206 Elo on a 0-100 height axis would sit beside a percentage as though the
// two measured the same thing.
assert.deepEqual(model.rows.map((row) => row.id), ['kept'], 'only percent tracks are plotted');
assert.equal(model.rows[0].domain, 'Math');
assert.equal(model.rows[0].reports, 4);
assert.equal(model.rows[0].name, 'Kept');
// Benchmarks under the report floor are counted, not silently dropped: the
// caption reports how many the figure leaves out.
assert.equal(model.omitted, 1, 'the 2-report benchmark is counted as omitted');

assert.equal(hist.scoreHistogramRows(bench, entries, 50).rows.length, 0, 'the cutoff hides a 60 from a <50 view');
assert.equal(hist.scoreHistogramRows({}, [], 100).rows.length, 0);

// Every bar needs its own footprint, or the front one hides the back one.
const tied = {
  a: {unit: 'percent', score_summary: {numeric_count: 3, display_max: 70}, observations: obs(3, '2026-02-01', 70)},
  b: {unit: 'percent', score_summary: {numeric_count: 3, display_max: 80}, observations: obs(3, '2026-02-01', 80)},
  c: {unit: 'percent', score_summary: {numeric_count: 3, display_max: 90}, observations: obs(3, '2026-02-01', 90)},
};
const lanes = hist.scoreHistogramRows(tied, [], 100);
assert.equal(lanes.rows.length, 3);
assert.equal(new Set(lanes.rows.map((row) => `${row.first}|${row.reports}|${row.lane}`)).size, 3,
  'three benchmarks sharing a date and a report count get three distinct lanes');

console.log('Date windows, deduplication, cutoff boundaries, source-neutral ranking, shared scale, and benchmark bars passed.');
