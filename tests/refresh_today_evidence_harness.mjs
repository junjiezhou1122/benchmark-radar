// Executes the dashboard refresh logic against real app.js helpers to prove
// that returning to Today after visiting Trends fetches the evidence-bearing
// bootstrap payload and updates Today's observations rather than requesting
// radar-trends.json (which omits evidence_items).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, "..", "site", "assets", "app.js"), "utf8");

// Minimal browser/DOM stub for evaluating refreshData()
class StubNode {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.attributes = {};
    this._text = "";
    this.hidden = false;
  }
  set textContent(v) {
    this._text = String(v);
    this.children = [];
  }
  get textContent() {
    return this.children.length ? this.children.map((c) => c.textContent).join("") : this._text;
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  removeAttribute(k) {
    delete this.attributes[k];
  }
  append(c) {
    this.children.push(c);
  }
  replaceChildren(...c) {
    this.children = c;
  }
  addEventListener() {}
  querySelectorAll() {
    return [];
  }
  querySelector() {
    return null;
  }
  classList = { toggle: () => {}, add: () => {}, remove: () => {} };
}

const registry = new Map();
globalThis.document = {
  createElement: (tag) => new StubNode(tag),
  createElementNS: (_ns, tag) => new StubNode(tag),
  createTextNode: (v) => ({ tag: "#text", textContent: v }),
  getElementById: (id) => {
    if (!registry.has(id)) registry.set(id, new StubNode("div"));
    return registry.get(id);
  },
  addEventListener: () => {},
  querySelectorAll: () => [],
  querySelector: () => null,
};
globalThis.window = {
  addEventListener: () => {},
  location: { pathname: "/", search: "", hash: "" },
};
globalThis.byId = (id) => document.getElementById(id);
globalThis.rerenderCurrentView = () => {};

let requestedPath = null;
globalThis.fetch = async (path) => {
  requestedPath = path;
  if (path === "/data/radar-bootstrap.json") {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: 2,
        latest_date: "2026-08-25",
        days: [
          {
            date: "2026-08-25",
            evidence_items: [
              {
                id: "item-new",
                title: "New Updated Evidence",
                source: "GitHub",
                published_at: "2026-08-25T10:00:00Z",
              },
            ],
            attention: { observations: [] },
            ingest_health: [],
            producer_health: [],
          },
        ],
        facets: { dates: ["2026-08-25"] },
        corpus: { aggregates: {} },
      }),
    };
  }
  if (path === "/data/radar-trends.json") {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: 2,
        latest_date: "2026-08-25",
        days: [
          {
            date: "2026-08-25",
            category_counts: { reasoning: 1 },
          },
        ],
        facets: { dates: ["2026-08-25"] },
      }),
    };
  }
  throw new Error(`Unexpected fetch path: ${path}`);
};

// Slice out state, mergeDashboardData, applyDashboardData, refreshData without running initialize()
const start = source.indexOf("const state = {");
const end = source.indexOf("\nasync function initialize()", start);
if (start < 0 || end < 0) throw new Error("Dashboard logic not found in app.js");

const harness = `${source.slice(start, end)}
globalThis.__harness = {
  state,
  allObservations,
  refreshData,
  applyDashboardData,
};`;

new Function(harness)();

const { state, allObservations, refreshData } = globalThis.__harness;

// Step 1: User opens Today with initial baseline evidence
state.data = {
  schema_version: 2,
  latest_date: "2026-08-25",
  days: [
    {
      date: "2026-08-25",
      evidence_items: [
        {
          id: "item-old",
          title: "Old Initial Evidence",
          source: "GitHub",
          published_at: "2026-08-25T08:00:00Z",
        },
      ],
      attention: { observations: [] },
      ingest_health: [],
      producer_health: [],
    },
  ],
  facets: { dates: ["2026-08-25"] },
  corpus: { aggregates: {} },
};
state.view = "today";
state.todayDate = "2026-08-25";
const initialObservations = allObservations();

// Step 2: User visits Trends and lets its payload load
state.view = "trends";
state.trendsDataLoaded = true;

// Step 3: User returns to Today
state.view = "today";

// Step 4: User clicks Refresh on Today
await refreshData();

const updatedItem = state.data?.days?.[0]?.evidence_items?.[0];
const refreshedObservations = allObservations();
console.log(
  JSON.stringify({
    requestedPath,
    initialObservationId: initialObservations[0]?.id,
    refreshedEvidenceId: updatedItem?.id,
    refreshedEvidenceTitle: updatedItem?.title,
    refreshedObservationId: refreshedObservations[0]?.id,
    refreshedObservationTitle: refreshedObservations[0]?.title,
  })
);
