import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, "..", "site", "assets", "app.js"), "utf8");

class StubNode {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = { setProperty() {} };
    this.classList = { toggle() {}, add() {}, remove() {} };
    this.hidden = false;
    this.open = false;
    this.checked = false;
    this.value = "";
    this._text = "";
    this.listeners = {};
  }
  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }
  get textContent() {
    return this.children.length ? this.children.map((child) => child.textContent || "").join("") : this._text;
  }
  setAttribute(key, value) {
    this.attributes[key] = String(value);
  }
  removeAttribute(key) {
    delete this.attributes[key];
  }
  append(...children) {
    this.children.push(...children.filter(Boolean));
  }
  replaceChildren(...children) {
    this.children = children.filter(Boolean);
  }
  addEventListener(type, listener) {
    (this.listeners[type] ||= []).push(listener);
  }
  async dispatch(type, event = {}) {
    for (const listener of this.listeners[type] || []) await listener(event);
  }
  querySelectorAll() {
    return [];
  }
  querySelector() {
    return null;
  }
  matches() {
    return false;
  }
}

const registry = new Map();
const allNodes = [];
const node = (tag = "div") => {
  const created = new StubNode(tag);
  allNodes.push(created);
  return created;
};
const getNode = (id) => {
  if (!registry.has(id)) registry.set(id, node("div"));
  return registry.get(id);
};

globalThis.document = {
  createElement: node,
  createElementNS: (_namespace, tag) => node(tag),
  createTextNode: (value) => ({ textContent: String(value) }),
  getElementById: getNode,
  querySelectorAll: () => [],
  querySelector: () => null,
};
globalThis.window = {
  history: { pushState() {}, replaceState() {} },
  location: { pathname: "/trends/", search: "", hash: "" },
  scrollTo() {},
};
globalThis.byId = getNode;
globalThis.getLang = () => "en";
globalThis.t = (value) => value;
globalThis.formatDate = (value) => String(value);
globalThis.countMapText = (value) => JSON.stringify(value || {});
globalThis.healthSummary = () => "";
globalThis.sourceMixCell = () => node("span");
globalThis.zeroItemSources = () => [];
globalThis.renderSourceGapNote = () => {};
globalThis.hideDayTooltip = () => {};
globalThis.showDayTooltip = () => {};
globalThis.console.error = () => {};

let releaseFullResponse;
globalThis.fetch = (path) => {
  if (path !== "/data/radar.json") throw new Error(`Unexpected fetch path: ${path}`);
  return new Promise((resolve) => {
    releaseFullResponse = () => resolve({
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: 2,
        latest_date: "2026-09-05",
        days: [
          { date: "2026-07-23", evidence_items: [], attention: { observations: [] } },
          { date: "2026-09-05", evidence_items: [], attention: { observations: [] } },
        ],
        facets: { dates: ["2026-07-23", "2026-09-05"], categories: [] },
        corpus: { entities: [], edges: [], aggregates: {} },
      }),
    });
  });
};

const start = source.indexOf("const state = {");
const end = source.indexOf("\nasync function initialize()", start);
if (start < 0 || end < 0) throw new Error("Dashboard logic not found in app.js");
const dashboardSource = source.slice(start, end).replace(
  "function renderToday(",
  "function renderToday_unused(",
);
const harness = `${dashboardSource}
globalThis.renderToday = () => {};
globalThis.__harness = {
  state,
  renderTrends,
  ensureFullData,
  bumpNavigation: () => ++viewNavigationSequence,
};
`;
new Function(harness)();

const { state, renderTrends, ensureFullData, bumpNavigation } = globalThis.__harness;
state.data = {
  schema_version: 2,
  latest_date: "2026-09-05",
  snapshot_count: 2,
  days: [
    {
      date: "2026-07-23",
      evidence_count: 1,
      category_counts: {},
      category_counts_released: {},
      event_kind_counts: {},
      attention: { active_count: 0, new_count: 0, observations: [] },
      category_trends: {},
      ingest_health: [],
      selection: {},
    },
    {
      date: "2026-09-05",
      evidence_count: 1,
      category_counts: {},
      category_counts_released: {},
      event_kind_counts: {},
      attention: { active_count: 0, new_count: 0, observations: [] },
      category_trends: {},
      ingest_health: [],
      selection: {},
    },
  ],
  facets: { dates: ["2026-07-23", "2026-09-05"], categories: [] },
  corpus: { aggregates: {} },
};
state.view = "trends";
state.todayDate = "2026-09-05";
renderTrends();

const historicalColumn = allNodes.find((candidate) => candidate.tag === "button" && candidate.listeners.click);
if (!historicalColumn) throw new Error("Historical Trends column was not rendered");
await historicalColumn.dispatch("click");
if (!releaseFullResponse) throw new Error("Historical click did not start the full-data request");

const initialDate = state.todayDate;
bumpNavigation();
state.view = "today";
state.todayDate = "2026-09-05";
const dateAfterTodayNavigation = state.todayDate;
releaseFullResponse();
await ensureFullData();
await new Promise((resolve) => setTimeout(resolve, 0));

console.log(JSON.stringify({
  initialDate,
  dateAfterTodayNavigation,
  dateAfterDelayedResponse: state.todayDate,
}));
