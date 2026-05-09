import type { SupabaseClient } from "@supabase/supabase-js";

export type DailyEvidenceArtifact = {
  run_id: string;
  artifact_type: string;
  storage_path: string;
  source_path: string;
  filename: string;
  content_type: string;
};

export type DailyEvidenceRun = {
  run_id: string;
  status: string;
  run_timestamp: string;
  report_date: string;
  mode: string;
  requested_batch_size: number;
  summary: Record<string, unknown>;
  publication_status: string;
  publication_errors: string[];
  local_run_folder: string;
  artifacts: DailyEvidenceArtifact[];
};

export interface DailyEvidenceRunRepository {
  getLatestRun(): Promise<DailyEvidenceRun | null>;
}

export class SupabaseDailyEvidenceRunRepository
  implements DailyEvidenceRunRepository
{
  private readonly supabase: SupabaseClient;

  constructor(supabase: SupabaseClient) {
    this.supabase = supabase;
  }

  async getLatestRun(): Promise<DailyEvidenceRun | null> {
    const { data, error } = await this.supabase
      .from("daily_evidence_runs")
      .select(
        "run_id,status,run_timestamp,report_date,mode,requested_batch_size,summary,publication_status,publication_errors,local_run_folder"
      )
      .eq("publication_status", "published")
      .order("run_timestamp", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (error) {
      throw error;
    }

    if (!data) {
      return null;
    }

    const { data: artifacts, error: artifactsError } = await this.supabase
      .from("daily_evidence_artifacts")
      .select("run_id,artifact_type,storage_path,source_path,filename,content_type")
      .eq("run_id", String(data.run_id))
      .order("artifact_type", { ascending: true })
      .order("filename", { ascending: true });

    if (artifactsError) {
      throw artifactsError;
    }

    return {
      ...(data as Omit<DailyEvidenceRun, "artifacts">),
      artifacts: (artifacts ?? []) as DailyEvidenceArtifact[]
    };
  }
}

export function createDailyEvidenceRunRepository(
  supabase: SupabaseClient
): DailyEvidenceRunRepository {
  return new SupabaseDailyEvidenceRunRepository(supabase);
}

type LabeledValue = {
  label: string;
  value: string;
};

type AvailableArtifactLink = {
  label: string;
  available: true;
  status: "Available";
  href: string;
  filename: string;
};

type UnavailableArtifactLink = {
  label: string;
  available: false;
  status: "Unavailable";
};

type ArtifactLink = AvailableArtifactLink | UnavailableArtifactLink;

type EmptyDailyEvidenceRunView = {
  state: "empty";
  message: string;
};

type AvailableDailyEvidenceRunView = {
  state: "available";
  runId: string;
  runStatus: LabeledValue;
  publicationStatus: LabeledValue;
  runTimestamp: LabeledValue;
  reportDate: LabeledValue;
  mode: LabeledValue;
  requestedBatchSize: LabeledValue;
  summaryFields: LabeledValue[];
  artifacts: ArtifactLink[];
};

export type DailyEvidenceRunView =
  | EmptyDailyEvidenceRunView
  | AvailableDailyEvidenceRunView;

type ArtifactSpec = {
  label: string;
  matches: (artifact: DailyEvidenceArtifact) => boolean;
};

const ARTIFACT_SPECS: ArtifactSpec[] = [
  {
    label: "Cross-Video Pattern Summary",
    matches: (artifact) =>
      artifact.filename === "cross_video_pattern_summary.json" ||
      artifact.storage_path.includes("cross_video_pattern_summary.json")
  },
  {
    label: "Final Markdown",
    matches: (artifact) => artifact.artifact_type === "markdown"
  },
  {
    label: "Structured JSON",
    matches: (artifact) =>
      artifact.artifact_type === "json" ||
      artifact.filename === "structured_batch_analysis.json"
  },
  {
    label: "Spreadsheet",
    matches: (artifact) => artifact.artifact_type === "spreadsheet"
  },
  {
    label: "Raw Scrape",
    matches: (artifact) => artifact.artifact_type === "raw_scrape"
  },
  {
    label: "Daily Top-5 Selection",
    matches: (artifact) => artifact.artifact_type === "daily_selection"
  }
];

export function buildDailyEvidenceRunView(
  run: DailyEvidenceRun | null,
  supabaseUrl: string
): DailyEvidenceRunView {
  if (!run) {
    return {
      state: "empty",
      message: "No cloud-published Daily Evidence Run is available yet."
    };
  }

  return {
    state: "available",
    runId: run.run_id,
    runStatus: { label: "Run status", value: formatValue(run.status) },
    publicationStatus: {
      label: "Publication",
      value: formatValue(run.publication_status)
    },
    runTimestamp: {
      label: "Run timestamp",
      value: formatValue(run.run_timestamp)
    },
    reportDate: { label: "Report date", value: formatValue(run.report_date) },
    mode: { label: "Mode", value: formatValue(run.mode) },
    requestedBatchSize: {
      label: "Requested batch size",
      value: formatValue(run.requested_batch_size)
    },
    summaryFields: buildSummaryFields(run.summary),
    artifacts: ARTIFACT_SPECS.map((spec) =>
      buildArtifactLink(spec, run.artifacts, supabaseUrl)
    )
  };
}

function buildSummaryFields(summary: Record<string, unknown>): LabeledValue[] {
  const fields: LabeledValue[] = [];
  const selectedCandidateCount = summary.selected_candidate_count;
  const sourceVideoCount = summary.source_video_count;
  const recommendation = isRecord(summary.recommendation)
    ? summary.recommendation
    : {};
  const whatToShootFirst = recommendation.what_to_shoot_first;

  if (selectedCandidateCount !== undefined) {
    fields.push({
      label: "Selected candidates",
      value: formatValue(selectedCandidateCount)
    });
  }
  if (sourceVideoCount !== undefined) {
    fields.push({
      label: "Source videos",
      value: formatValue(sourceVideoCount)
    });
  }
  if (whatToShootFirst !== undefined) {
    fields.push({
      label: "Shoot first",
      value: formatValue(whatToShootFirst)
    });
  }

  if (fields.length === 0) {
    fields.push({ label: "Summary", value: "No summary fields published" });
  }

  return fields;
}

function buildArtifactLink(
  spec: ArtifactSpec,
  artifacts: DailyEvidenceArtifact[],
  supabaseUrl: string
): ArtifactLink {
  const artifact = artifacts.find(spec.matches);

  if (!artifact) {
    return {
      label: spec.label,
      available: false,
      status: "Unavailable"
    };
  }

  return {
    label: spec.label,
    available: true,
    status: "Available",
    href: artifactHref(artifact.storage_path, supabaseUrl),
    filename: artifact.filename
  };
}

function artifactHref(storagePath: string, supabaseUrl: string): string {
  if (/^https?:\/\//i.test(storagePath)) {
    return storagePath;
  }

  const baseUrl = supabaseUrl.replace(/\/$/, "");
  return `${baseUrl}/storage/v1/object/public/${storagePath
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}

function formatValue(value: unknown): string {
  if (typeof value === "number") {
    return new Intl.NumberFormat("en-US").format(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return "Unavailable";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
