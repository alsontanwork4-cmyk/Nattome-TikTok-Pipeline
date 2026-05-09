import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildDailyEvidenceRunHistoryView,
  buildDailyEvidenceRunView,
  createDailyEvidenceRunRepository
} from "./dailyEvidenceRuns.ts";

class FakeSupabaseClient {
  constructor({ runs = [], artifacts = [] } = {}) {
    this.runs = runs;
    this.artifacts = artifacts;
    this.calls = [];
  }

  from(tableName) {
    this.calls.push({ tableName });
    return new FakeQuery(this, tableName);
  }
}

class FakeQuery {
  constructor(client, tableName) {
    this.client = client;
    this.tableName = tableName;
    this.filters = [];
    this.orders = [];
    this.limitCount = null;
  }

  select(columns) {
    this.columns = columns;
    return this;
  }

  eq(column, value) {
    this.filters.push({ column, value });
    return this;
  }

  order(column, options = {}) {
    this.orders.push({ column, ascending: options.ascending !== false });
    return this;
  }

  limit(count) {
    this.limitCount = count;
    return this;
  }

  async maybeSingle() {
    const rows = this.resolveRows();
    return { data: rows[0] ?? null, error: null };
  }

  then(resolve, reject) {
    return Promise.resolve({ data: this.resolveRows(), error: null }).then(
      resolve,
      reject
    );
  }

  resolveRows() {
    const source =
      this.tableName === "daily_evidence_runs"
        ? this.client.runs
        : this.client.artifacts;
    let rows = [...source];

    for (const filter of this.filters) {
      rows = rows.filter((row) => row[filter.column] === filter.value);
    }

    for (const order of [...this.orders].reverse()) {
      rows.sort((left, right) => {
        const leftValue = left[order.column] ?? "";
        const rightValue = right[order.column] ?? "";
        const comparison = String(leftValue).localeCompare(String(rightValue));
        return order.ascending ? comparison : -comparison;
      });
    }

    if (this.limitCount !== null) {
      rows = rows.slice(0, this.limitCount);
    }

    return rows;
  }
}

const publishedRun = {
  run_id: "20260509T010000Z_daily",
  status: "completed",
  run_timestamp: "2026-05-09T01:00:00Z",
  report_date: "2026-05-09",
  mode: "daily",
  requested_batch_size: 5,
  summary: {
    selected_candidate_count: 5,
    source_video_count: 5,
    recommendation: {
      what_to_shoot_first: "Gut routine with visible prep proof"
    }
  },
  publication_status: "published",
  publication_errors: [],
  local_run_folder: "runs/batch-analysis/20260509T010000Z_daily"
};

test("repository loads the newest published daily evidence run with artifacts", async () => {
  const client = new FakeSupabaseClient({
    runs: [
      { ...publishedRun, run_id: "draft", publication_status: "pending" },
      { ...publishedRun, run_id: "older", run_timestamp: "2026-05-08T01:00:00Z" },
      publishedRun
    ],
    artifacts: [
      {
        run_id: publishedRun.run_id,
        artifact_type: "markdown",
        storage_path: "daily-runs/20260509T010000Z_daily/outputs/final.md",
        source_path: "outputs/final.md",
        filename: "final.md",
        content_type: "text/markdown"
      }
    ]
  });

  const latestRun = await createDailyEvidenceRunRepository(client).getLatestRun();

  assert.equal(latestRun.run_id, "20260509T010000Z_daily");
  assert.equal(latestRun.publication_status, "published");
  assert.equal(latestRun.artifacts.length, 1);
  assert.deepEqual(
    client.calls.map((call) => call.tableName),
    ["daily_evidence_runs", "daily_evidence_artifacts"]
  );
});

test("run view exposes summary and available Daily Output Set links", () => {
  const view = buildDailyEvidenceRunView(
    {
      ...publishedRun,
      artifacts: [
        {
          run_id: publishedRun.run_id,
          artifact_type: "batch_analysis",
          storage_path:
            "daily-runs/20260509T010000Z_daily/run/data/cross_video_pattern_summary.json",
          source_path: "runs/data/cross_video_pattern_summary.json",
          filename: "cross_video_pattern_summary.json",
          content_type: "application/json"
        },
        {
          run_id: publishedRun.run_id,
          artifact_type: "markdown",
          storage_path: "daily-runs/20260509T010000Z_daily/outputs/final.md",
          source_path: "outputs/final.md",
          filename: "final.md",
          content_type: "text/markdown"
        },
        {
          run_id: publishedRun.run_id,
          artifact_type: "json",
          storage_path:
            "daily-runs/20260509T010000Z_daily/run/data/structured_batch_analysis.json",
          source_path: "runs/data/structured_batch_analysis.json",
          filename: "structured_batch_analysis.json",
          content_type: "application/json"
        },
        {
          run_id: publishedRun.run_id,
          artifact_type: "spreadsheet",
          storage_path: "daily-runs/20260509T010000Z_daily/outputs/brief.xlsx",
          source_path: "outputs/brief.xlsx",
          filename: "brief.xlsx",
          content_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
        {
          run_id: publishedRun.run_id,
          artifact_type: "raw_scrape",
          storage_path: "daily-runs/20260509T010000Z_daily/inputs/raw_scrape_top30.json",
          source_path: "data/raw_scrape_top30.json",
          filename: "raw_scrape_top30.json",
          content_type: "application/json"
        },
        {
          run_id: publishedRun.run_id,
          artifact_type: "daily_selection",
          storage_path:
            "daily-runs/20260509T010000Z_daily/inputs/daily_selection_top5.json",
          source_path: "data/daily_selection_top5.json",
          filename: "daily_selection_top5.json",
          content_type: "application/json"
        }
      ]
    },
    "https://example.supabase.co"
  );

  assert.equal(view.state, "available");
  assert.equal(view.runStatus.value, "completed");
  assert.equal(view.publicationStatus.value, "published");
  assert.equal(view.reportDate.value, "2026-05-09");
  assert.equal(
    view.summaryFields.find((field) => field.label === "Selected candidates").value,
    "5"
  );
  assert.equal(
    view.artifacts.find((artifact) => artifact.label === "Cross-Video Pattern Summary")
      .href,
    "https://example.supabase.co/storage/v1/object/public/daily-runs/20260509T010000Z_daily/run/data/cross_video_pattern_summary.json?download=cross_video_pattern_summary.json"
  );
  assert.ok(view.artifacts.every((artifact) => artifact.available));
});

test("run view marks missing artifacts unavailable", () => {
  const view = buildDailyEvidenceRunView(
    {
      ...publishedRun,
      artifacts: [
        {
          run_id: publishedRun.run_id,
          artifact_type: "markdown",
          storage_path: "daily-runs/20260509T010000Z_daily/outputs/final.md",
          source_path: "outputs/final.md",
          filename: "final.md",
          content_type: "text/markdown"
        }
      ]
    },
    "https://example.supabase.co"
  );

  assert.equal(
    view.artifacts.find((artifact) => artifact.label === "Final Markdown").available,
    true
  );
  assert.equal(
    view.artifacts.find((artifact) => artifact.label === "Structured JSON").available,
    false
  );
  assert.equal(
    view.artifacts.find((artifact) => artifact.label === "Structured JSON").status,
    "Unavailable"
  );
});

test("run view returns the empty state when no cloud runs exist", () => {
  const view = buildDailyEvidenceRunView(null, "https://example.supabase.co");

  assert.deepEqual(view, {
    state: "empty",
    message: "No cloud-published Daily Evidence Run is available yet."
  });
});

test("repository lists run history across publication states", async () => {
  const client = new FakeSupabaseClient({
    runs: [
      { ...publishedRun, run_id: "published", publication_status: "published" },
      { ...publishedRun, run_id: "incomplete", publication_status: "pending" },
      { ...publishedRun, run_id: "failed", publication_status: "artifact_failed" }
    ]
  });

  const history = await createDailyEvidenceRunRepository(client).listRuns();

  assert.deepEqual(
    history.map((run) => run.publication_status),
    ["published", "pending", "artifact_failed"]
  );
  assert.ok(history.every((run) => run.artifacts.length === 0));
});

test("repository loads a run detail by id with artifacts", async () => {
  const client = new FakeSupabaseClient({
    runs: [
      { ...publishedRun, run_id: "target-run" },
      { ...publishedRun, run_id: "other-run" }
    ],
    artifacts: [
      {
        run_id: "target-run",
        artifact_type: "json",
        storage_path: "daily-runs/target-run/run/data/structured_batch_analysis.json",
        source_path: "runs/data/structured_batch_analysis.json",
        filename: "structured_batch_analysis.json",
        content_type: "application/json"
      },
      {
        run_id: "other-run",
        artifact_type: "markdown",
        storage_path: "daily-runs/other-run/outputs/final.md",
        source_path: "outputs/final.md",
        filename: "final.md",
        content_type: "text/markdown"
      }
    ]
  });

  const run = await createDailyEvidenceRunRepository(client).getRunById("target-run");

  assert.equal(run.run_id, "target-run");
  assert.equal(run.artifacts.length, 1);
  assert.equal(run.artifacts[0].filename, "structured_batch_analysis.json");
});

test("history view links each run to its detail route", () => {
  const view = buildDailyEvidenceRunHistoryView([
    { ...publishedRun, run_id: "20260509T010000Z_daily", artifacts: [] },
    {
      ...publishedRun,
      run_id: "20260508T010000Z_daily",
      status: "partial",
      publication_status: "artifact_failed",
      artifacts: []
    }
  ]);

  assert.equal(view.state, "available");
  assert.deepEqual(
    view.runs.map((run) => [run.runId, run.href, run.status.value, run.publication.value]),
    [
      [
        "20260509T010000Z_daily",
        "/runs/20260509T010000Z_daily",
        "completed",
        "published"
      ],
      [
        "20260508T010000Z_daily",
        "/runs/20260508T010000Z_daily",
        "partial",
        "artifact_failed"
      ]
    ]
  );
});

test("artifact links are downloadable public Supabase URLs without service role data", () => {
  const view = buildDailyEvidenceRunView(
    {
      ...publishedRun,
      artifacts: [
        {
          run_id: publishedRun.run_id,
          artifact_type: "markdown",
          storage_path: "daily-runs/20260509T010000Z_daily/outputs/final.md",
          source_path: "outputs/final.md",
          filename: "final.md",
          content_type: "text/markdown"
        }
      ]
    },
    "https://example.supabase.co"
  );
  const link = view.artifacts.find((artifact) => artifact.label === "Final Markdown");

  assert.equal(link.available, true);
  assert.equal(
    link.href,
    "https://example.supabase.co/storage/v1/object/public/daily-runs/20260509T010000Z_daily/outputs/final.md?download=final.md"
  );
  assert.equal(link.href.includes("SUPABASE_SERVICE_ROLE_KEY"), false);
  assert.equal(link.href.includes("service_role"), false);
});
