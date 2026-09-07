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
state.lscore = 'under70';
const scoreNames = ['scoreRecord','matchesScoreFilter','scoreBrowseRows','frontierDefaultEntry','externalDisplayFactor'];
const scores = new Function('state', `${scoreNames.map(fn).join('\n')}\nreturn {${scoreNames.join(',')}};`)(state);
assert.deepEqual(scores.scoreBrowseRows().map(r=>[r.id,r.rank]), [['external',1],['curated',2]]);
assert.equal(scores.frontierDefaultEntry(state.data.model_card_leaderboard).id,'external');
assert.equal(scores.matchesScoreFilter(summary(69.999)),true);
assert.equal(scores.matchesScoreFilter(summary(70)),false);
assert.equal(scores.matchesScoreFilter(summary(60,0)),false);
state.lscore='under100';
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['over70','external','curated']);
state.lscore='all';
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['at100','over70','external','curated']);
state.benchmarkIndex=null;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['curated']);
assert.equal(scores.externalDisplayFactor({score_summary:{display_multiplier:100}}),100);
assert.equal(scores.externalDisplayFactor({score_summary:{display_multiplier:1}}),1);
console.log('Date windows, deduplication, cutoff boundaries, source-neutral ranking, and shared scale passed.');
