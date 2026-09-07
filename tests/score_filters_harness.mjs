// Execute production functions with small deterministic inputs, without a browser.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { skylineModel, skylineGeometry, skylineFrontierSteps, scorePopulation, matchesScoreCutoff } from '../site/assets/skyline.js';
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
const scores = new Function('state', 'scorePopulation', 'matchesScoreCutoff', `${scoreNames.map(fn).join('\n')}\nreturn {${scoreNames.join(',')}};`)(state, scorePopulation, matchesScoreCutoff);
assert.deepEqual(scores.scoreBrowseRows().map(r=>[r.id,r.rank]), [['external',1],['curated',2],['missing',3]]);
assert.equal(scores.frontierDefaultEntry(state.data.model_card_leaderboard).id,'external');
assert.equal(scores.matchesScoreFilter(summary(69.999)),true);
assert.equal(scores.matchesScoreFilter(summary(70)),false);
assert.equal(scores.matchesScoreFilter(summary(60,0)),true);
state.lscore=100;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['at100','over70','external','curated','missing']);
state.lscore=90;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['over70','external','curated','missing']);
// An intermediate step the old three-option filter could not express.
state.lscore=40;
assert.deepEqual(scores.scoreBrowseRows().map(r=>r.id), ['missing']);
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

// --- Benchmark Frontier: identity, normalization and dominance ----------------
const entry = (id, count, extra = {}) => ({
  benchmark_id: id, name: id, released: '2025-01-01', domain: 'science',
  // A deliberately wrong summary guards against ever using it or score counts.
  card_count: 999,
  adopters: Array.from({length: count}, (_, n) => ({
    model_card_id: `card-${n}`, published: '2026-01-01', url: `https://example.org/${n}`,
  })), ...extra,
});
const record = (value, extra = {}) => ({
  unit: 'percent', direction: 'higher_is_better', metric: 'accuracy',
  observations: [{value, source_id: 'card-0', reported_at: '2026-01-01'}], ...extra,
});
const tracks = {
  hardest: record(10), twin: record(10), adopted: record(20),
  dominated: record(30), sameScore: record(20), sameAdoption: record(21),
  all: record(100), zero: record(0),
};
const cards = [entry('hardest',2), entry('twin',2,{released:'2020-01-01'}),
  entry('adopted',5), entry('dominated',4), entry('sameScore',3),
  entry('sameAdoption',5), entry('all',6), entry('zero',0)];
const model = skylineModel(tracks,cards,[],100);
const paretoIds = (m) => m.rows.filter((row)=>row.pareto).map((row)=>row.id).sort();
assert.deepEqual(paretoIds(model), ['adopted','all','hardest','twin','zero']);
assert.equal(model.rows.length,8,'coincident benchmarks retain their identities');
assert.equal(model.rows.find(r=>r.id==='zero').adoption,0,'known zero adoption stays valid');
assert.equal(model.rows.find(r=>r.id==='twin').date,'2020-01-01','time is displayed but never used for dominance');
for (let cut = 10; cut <= 100; cut += 10) {
  const sliced = skylineModel(tracks,cards,[],cut);
  assert.deepEqual(sliced.rows, model.rows.filter((row)=>cut===100 || row.score<cut));
  assert.equal(sliced.rows.some(row=>row.score===cut),cut===100,'cutoff is strict except All');
  assert.deepEqual(skylineGeometry(sliced.eligible).project(.5,20,2),
    skylineGeometry(model.eligible).project(.5,20,2),'a slice never rescales its survivors');
}
const duplicate = entry('repeats',2);
duplicate.adopters.push({...duplicate.adopters[0]});
const duplicated = skylineModel({repeats:record(45,{observations:Array(100).fill({value:45})})},[duplicate],[],100);
assert.equal(duplicated.rows[0].adoption,2,'repeated cards and repeated score rows cannot inflate adoption');
assert.equal(duplicated.rows[0].score,45);
const reversed = skylineModel({error:record(90,{
  direction:'lower_is_better',observations:[{value:90},{value:25}],
})},[entry('error',1)],[],100);
assert.equal(reversed.rows[0].score,75,'best normalized score is 100 minus the LOWEST error');
assert.equal(reversed.rows[0].rawScore,25);
assert.equal(skylineModel({error:record(25,{direction:'lower_is_better'})},[entry('error',1)],[],70).rows.length,0);
const invalids = {
  elo:record(50,{unit:'elo'}), dollars:record(5,{unit:'usd'}),
  fraction:record(.7,{unit:undefined}), unknown:record(30,{direction:undefined}),
  bogus:record(30,{direction:'inferred'}), negative:record(-1), high:record(101),
  unscored:record(null), unmeasured:record(10), undated:record(10,{observations:[{value:10}]}),
};
const invalidModel = skylineModel(invalids,
  Object.keys(invalids).filter(id=>id!=='unmeasured').map(id=>entry(id,0,{released:null})),[],100);
assert.deepEqual(invalidModel.rows,[]);
assert.equal(invalidModel.pending.length,10,'missing fields never remove a benchmark');
assert.equal(invalidModel.all.filter(row=>row.missing.includes('scale')).length,7);
assert.equal(invalidModel.all.find(row=>row.id==='unmeasured').adoption,null,'unknown adoption is not zero');
assert.equal(invalidModel.all.find(row=>row.id==='unscored').score,null,'unknown score is not zero');
assert.equal(invalidModel.population,10);
assert(invalidModel.pending.filter(row=>row.missing.includes('score') || row.missing.includes('scale') || row.missing.includes('adoption'))
  .every(row=>row.pareto===null),'unknown score or adoption cannot qualify for Pareto');
const dateIndependent=skylineModel({dated:record(50),undated:record(10,{observations:[{value:10}]})},
  [entry('dated',1),entry('undated',2,{released:null,adopters:[{model_card_id:'a'},{model_card_id:'b'}]})],[],100);
assert.equal(dateIndependent.rows[0].pareto,false,'a benchmark with unknown time can still dominate');
assert.equal(dateIndependent.pending[0].pareto,true,'time never participates in Pareto eligibility');
assert.equal(dateIndependent.comparable.length,2,'both points can be projected on the score/adoption wall');
const datesModel = skylineModel({date:record(40,{first_reported_at:'2024-04-03'})},
  [entry('date',1,{released:'2026-02-30',adopters:[{model_card_id:'x',published:'2023-12-11'}]})],[],100);
assert.equal(datesModel.rows[0].date,'2023-12-11','earliest actual evidence is used if release is absent or invalid');
assert.equal(datesModel.rows[0].dateBasis,'observed');
assert.equal(model.rows.find(r=>r.id==='hardest').sourceUrl,'https://example.org/0');
assert.equal(model.rows.find(r=>r.id==='hardest').domain,'Science');
assert.equal(skylineModel({other:record(20)},[entry('other',1,{domain:'unmapped'})],[],100).rows[0].domain,'Other');
assert.deepEqual(skylineFrontierSteps(model.rows),[
  {score:0,adoption:0},{score:10,adoption:0},{score:10,adoption:2},
  {score:20,adoption:2},{score:20,adoption:5},{score:100,adoption:5},{score:100,adoption:6},
],'staircase corners use raw score and adoption, with shared corners drawn once');
const g = skylineGeometry(model.eligible);
assert(g.project(1,0)[0]>g.project(0,0)[0],'time increases to the right');
assert(g.project(.5,0)[1]>g.project(.5,100)[1],'low scores are in front');
assert(g.project(.5,20,5)[1]<g.project(.5,20,2)[1],'adoption grows upward');
assert(g.project(.5,20,1)[1]-g.project(.5,20,2)[1]
  >g.project(.5,20,5)[1]-g.project(.5,20,6)[1],'heights use a logarithmic scale');

// Exercise production SVG construction without a browser or a DOM.
function svgElement(tag,attrs={},text=null) {
  return {tag,attrs,text,children:[],append(...children){this.children.push(...children);}};
}
const translate = (key,params={})=>Object.entries(params).reduce((s,[k,v])=>s.replaceAll(`{${k}}`,v),key);
const chart = new Function('skylineGeometry','skylineFrontierSteps','svgElement','t','metricLabel','shorten','formatDate','makeFrontierPointInteractive','scoreSourceLabel',
  `${fn('skylineChart')}\nreturn skylineChart;`)(skylineGeometry,skylineFrontierSteps,svgElement,translate,
  (n,label)=>`${n} ${label}`, (s,n)=>s.slice(0,n), x=>x, (node,details)=>{node.details=details;}, x=>x);
const flatten = (node)=>[node,...node.children.flatMap(flatten)];
for (const cutoff of [10,70,100]) {
  const m=skylineModel(tracks,cards,[],cutoff);
  const nodes=flatten(chart(m,cutoff));
  assert.equal(nodes.filter(n=>'data-frontier-point' in n.attrs).length,m.rows.length);
  assert.equal(nodes.filter(n=>'data-frontier-anchor' in n.attrs).length,m.rows.length);
  assert.equal(nodes.filter(n=>n.attrs.class?.startsWith('skyline-projection ')).length,m.rows.length);
  assert.equal(nodes.filter(n=>n.attrs.class==='skyline-guide').length,m.rows.length);
  assert.equal(nodes.filter(n=>n.attrs.class==='skyline-slice').length,cutoff<100?1:0);
  assert.equal(new Set(nodes.filter(n=>'data-benchmark-id' in n.attrs).map(n=>n.attrs['data-benchmark-id'])).size,m.rows.length);
  assert(!JSON.stringify(nodes).includes('NaN'));
  assert(!JSON.stringify(nodes).includes('Infinity'));
  const labelLayer=nodes.find(n=>n.attrs.class==='skyline-labels');
  assert.equal(labelLayer.children.filter(n=>n.tag==='text').length,m.rows.filter(r=>r.pareto).length);
}
assert(!JSON.stringify(chart(skylineModel({},[],[],70),70)).includes('NaN'),'empty chart retains usable axes');
// A complete rebuilt corpus exercises crowded labels and the production input contract.
const corpus = JSON.parse(readFileSync('site/data/radar.json','utf8'));
const catalog = JSON.parse(readFileSync('site/data/benchmark-index.json','utf8')).benchmarks;
const benchmarkRecords=corpus.benchmark_score_progression.benchmarks;
const corpusEntries=corpus.model_card_leaderboard.entries;
const full=skylineModel(benchmarkRecords,corpusEntries,catalog,100);
const expected=catalog.length+Object.keys(benchmarkRecords).length;
assert.equal(full.population,expected);
assert.equal(full.visible.length,expected);
assert(full.population>=1259,'principle.md: investigate a corpus smaller than 1,259 records');
assert(full.sources>=4,'principle.md: every source belongs to the same population');
assert.equal(new Set(full.all.map(row=>row.id)).size,expected,'source rows are never silently merged');
assert.equal(full.all.filter(row=>row.source==='opencompass_hub').length,
  catalog.filter(row=>row.source==='opencompass_hub').length,'unscored OpenCompass records remain present');
state.data=corpus;
state.benchmarkIndex=catalog;
for(const cutoff of [10,30,70,100]) {
  state.lscore=cutoff;
  const current=skylineModel(benchmarkRecords,corpusEntries,catalog,cutoff);
  assert.deepEqual(current.visible,full.all.filter(row=>matchesScoreCutoff(row.summary,cutoff)));
  assert.equal(current.visible.length+current.hidden,expected);
  assert.equal(current.rows.length+current.pending.length,current.visible.length);
  assert.equal(current.unscored,full.unscored,'unknown scores stay visible at every cutoff');
  assert.deepEqual(current.visible.map(row=>row.id).sort(), scores.scoreBrowseRows().map(row=>row.id).sort(),
    'chart and browser must show exactly the same filtered record IDs');
  const rendered=chart(current,cutoff);
  const drawn=flatten(rendered);
  assert.equal(drawn.filter(node=>'data-benchmark-id' in node.attrs).length,current.visible.length,
    'every visible record has its own inspectable SVG mark');
  const maxY=Number(rendered.attrs.viewBox.split(' ').at(-1));
  for(const text of drawn.filter(n=>n.tag==='text')) {
    assert(text.attrs.x>=0 && text.attrs.x<=1110 && text.attrs.y>=0 && text.attrs.y<=maxY,
      `${text.text}: label anchor outside viewBox`);
  }
}
const selected=new Set([catalog.find(row=>row.source==='opencompass_hub').slug]);
const querySlice=skylineModel(benchmarkRecords,corpusEntries,catalog,70,selected);
assert.deepEqual(querySlice.visible.map(row=>row.id),[...selected]);
assert.equal(querySlice.population,expected,'a search never redefines the universe');
console.log('Full-corpus coverage, source parity, unknown measurements, score slicing, Pareto, and SVG construction passed.');
