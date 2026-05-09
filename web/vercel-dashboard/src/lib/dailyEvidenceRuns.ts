import type { SupabaseClient } from "@supabase/supabase-js";

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
};

export interface DailyEvidenceRunRepository {
  getLatestRun(): Promise<DailyEvidenceRun | null>;
}

export class SupabaseDailyEvidenceRunRepository
  implements DailyEvidenceRunRepository
{
  constructor(private readonly supabase: SupabaseClient) {}

  async getLatestRun(): Promise<DailyEvidenceRun | null> {
    const { data, error } = await this.supabase
      .from("daily_evidence_runs")
      .select(
        "run_id,status,run_timestamp,report_date,mode,requested_batch_size,summary,publication_status,publication_errors,local_run_folder"
      )
      .order("run_timestamp", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (error) {
      throw error;
    }

    return data as DailyEvidenceRun | null;
  }
}

export function createDailyEvidenceRunRepository(
  supabase: SupabaseClient
): DailyEvidenceRunRepository {
  return new SupabaseDailyEvidenceRunRepository(supabase);
}
