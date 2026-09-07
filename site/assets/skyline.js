// Benchmark-level measurements for the skyline. Catalog score observations
// never stand in for model-card adoption, and time never enters dominance.
export const SKYLINE_DOMAINS = {
  Code: ["coding", "code", "coding_agent"],
  Science: ["science", "biology", "math", "ai_research"],
  Agent: ["agent", "agents", "agentic", "tool_use", "computer_use"],
  Multimodal: ["multimodal", "vision", "image", "video", "audio", "spatial_reasoning", "vlm"],
  Other: [],
};

function validDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const time = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value;
}

// This is the population used by BOTH the chart and the browser. Keeping a
// row does not require a score, date, adoption count, or join to another source.
export function scoreBrowserSummary(record) {
  const values = (record.observations || []).map((row) => row.value).filter(Number.isFinite);
  const summary = record.score_summary || (values.length ? {
    numeric_count: values.length, display_max: Math.max(...values), unit: record.unit, display_multiplier: 1,
  } : null);
  if (record.unit === "percent" && record.direction === "lower_is_better"
    && values.length && values.every((value) => value >= 0 && value <= 100)) {
    return { ...summary, display_max: 100 - Math.min(...values), normalized_from_lower: true };
  }
  return summary;
}

export function scorePopulation(benchmarks = {}, entries = [], catalog = []) {
  const named = new Map(entries.map((entry) => [entry.benchmark_id, entry]));
  return [
    ...Object.entries(benchmarks).map(([id, record]) => ({
      id, name: named.get(id)?.name || id, source: "curated",
      curated: named.get(id), record, summary: scoreBrowserSummary(record),
    })),
    ...catalog.map((record) => ({
      id: record.slug, name: record.name, source: record.source,
      external: record, record, summary: record.score_summary,
    })),
  ];
}

export function matchesScoreCutoff(summary, cutoff) {
  // An unknown score is never silently treated as zero or as above the cutoff.
  return !Number.isFinite(summary?.display_max) || !summary.numeric_count
    || cutoff >= 100 || summary.display_max < cutoff;
}

export function skylineModel(benchmarks = {}, entries = [], catalog = [], cutoff = 70, matchingIds = null) {
  const population = scorePopulation(benchmarks, entries, catalog);
  const all = population.map((item) => {
    const { id, name, source, curated: entry, record, summary } = item;
    const observations = (record.observations || []).filter((row) => Number.isFinite(row.value));
    const direction = record.direction || record.score_direction;
    const unit = record.unit || summary?.unit;
    const percent = unit === "percent" && ["higher_is_better", "lower_is_better"].includes(direction);
    const inverted = percent && direction === "lower_is_better";
    const normalized = (row) => inverted ? 100 - row.value : row.value;
    const best = observations.length ? observations.reduce((a, b) => normalized(b) > normalized(a) ? b : a) : null;
    const rawScore = best?.value ?? summary?.raw_max ?? summary?.display_max ?? null;
    const displayScore = summary?.display_max ?? best?.value ?? null;
    const score = percent && (!inverted || best) && (best || Number.isFinite(displayScore))
      && observations.every((row) => row.value >= 0 && row.value <= 100)
      && displayScore >= 0 && displayScore <= 100
      ? best ? normalized(best) : displayScore : null;
    const adopters = entry?.adopters;
    const adoption = Array.isArray(adopters)
      && adopters.every((card) => typeof card.model_card_id === "string" && card.model_card_id)
      ? new Set(adopters.map((card) => card.model_card_id)).size : null;
    const released = entry?.released || record.released;
    const releaseKnown = validDate(released);
    const observed = [record.first_reported_at, record.first_observed?.slice(0, 10),
      ...observations.map((row) => row.reported_at), ...(adopters || []).map((card) => card.published)]
      .filter(validDate).sort()[0];
    const date = releaseKnown ? released : observed || null;
    const domainValues = [entry?.domain, ...(record.categories || []), record.modality]
      .filter(Boolean).map((value) => value.toLowerCase());
    const card = adopters?.find((card) => card.model_card_id === best?.source_id);
    const missing = [];
    if (!Number.isFinite(displayScore)) missing.push("score");
    else if (score === null) missing.push("scale");
    if (adoption === null) missing.push("adoption");
    if (!date) missing.push("date");
    return {
      id, name, source, summary, date, dateBasis: date ? releaseKnown ? "released" : "observed" : null,
      time: date ? Date.parse(`${date}T00:00:00Z`) : null,
      score, displayScore, rawScore, inverted, adoption, missing,
      domain: Object.keys(SKYLINE_DOMAINS).find((domain) => SKYLINE_DOMAINS[domain].some((value) => domainValues.includes(value))) || "Other",
      sourceUrl: card?.url || record.source_url || summary?.source_reference?.source_url,
      sourceId: best?.source_id, reportedAt: best?.reported_at,
      metric: record.metric, protocol: best?.protocol, instrument: best?.instrument,
    };
  });
  const eligible = all.filter((row) => !row.missing.length);
  for (const row of all) {
    row.pareto = row.missing.length ? null : !eligible.some((other) => other.score <= row.score && other.adoption >= row.adoption
      && (other.score < row.score || other.adoption > row.adoption));
  }
  // Cutoff membership is shared with score browsing. Normalized reversed
  // metrics remain explicit in the tooltip; they never change source scores.
  const visible = all.filter((row) => (!matchingIds || matchingIds.has(row.id)) && matchesScoreCutoff(row.summary, cutoff));
  return {
    all, visible, eligible, rows: visible.filter((row) => !row.missing.length),
    pending: visible.filter((row) => row.missing.length),
    population: all.length, sources: new Set(all.map((row) => row.source)).size,
    hidden: all.length - visible.length,
    unscored: visible.filter((row) => !Number.isFinite(row.displayScore)).length,
  };
}

export function skylineGeometry(eligible) {
  const times = eligible.map((row) => row.time).filter(Number.isFinite);
  const first = times.length ? Math.min(...times) : Date.UTC(2020, 0, 1);
  const last = times.length ? Math.max(...times) : first;
  const startYear = new Date(first).getUTCFullYear();
  const endYear = new Date(last).getUTCFullYear() + 1;
  const start = Date.UTC(startYear, 0, 1);
  const end = Date.UTC(endYear, 0, 1);
  const maximum = Math.max(1, ...eligible.map((row) => row.adoption).filter(Number.isFinite));
  // Oblique projection: time to the right, low scores at the front, adoption up.
  // Fixed domains across cutoffs prevent filtering from moving the surviving points.
  const project = (timeFraction, score, adoption = 0) => [
    320 + timeFraction * 660 - score * 2.3,
    475 - score * 1.5 - 265 * Math.log1p(adoption) / Math.log1p(maximum),
  ];
  const timeFraction = (time) => (time - start) / (end - start);
  return { width: 1110, height: 570, startYear, endYear, maximum, project, timeFraction };
}

export function skylineFrontierSteps(rows) {
  // Equal score/adoption pairs all remain Pareto. Draw their shared corner once.
  const frontier = rows.filter((row) => row.pareto)
    .sort((a, b) => a.score - b.score || a.id.localeCompare(b.id));
  const steps = [];
  for (const row of frontier) {
    const previous = steps.at(-1);
    if (previous?.score === row.score && previous.adoption === row.adoption) continue;
    if (previous) steps.push({ score: row.score, adoption: previous.adoption });
    steps.push({ score: row.score, adoption: row.adoption });
  }
  return steps;
}
