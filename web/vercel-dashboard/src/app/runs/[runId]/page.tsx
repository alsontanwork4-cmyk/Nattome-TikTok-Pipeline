import Link from "next/link";
import { notFound } from "next/navigation";

import {
  buildDailyEvidenceRunView,
  createDailyEvidenceRunRepository
} from "../../../lib/dailyEvidenceRuns";
import { requireAuthenticatedUser } from "../../../lib/auth";
import { requireSupabaseEnv } from "../../../lib/env";

type RunDetailPageProps = {
  params: Promise<{
    runId: string;
  }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { runId } = await params;
  const { supabase, user } = await requireAuthenticatedUser();
  const run = await createDailyEvidenceRunRepository(supabase).getRunById(
    decodeURIComponent(runId)
  );
  const runView = buildDailyEvidenceRunView(run, requireSupabaseEnv().url);

  if (runView.state === "empty") {
    notFound();
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <strong>Nattome</strong>
            <span>Private Daily Evidence Dashboard</span>
          </div>
          <span className="status-pill">Signed in as {user.email ?? user.id}</span>
        </div>
      </header>

      <section className="page">
        <div className="page-header">
          <div>
            <Link className="back-link" href="/">
              Back to run history
            </Link>
            <h1>{runView.runId}</h1>
            <p className="muted">Read-only Daily Evidence Run detail.</p>
          </div>
          <span className="status-pill">{runView.publicationStatus.value}</span>
        </div>

        <section className="panel" aria-labelledby="run-detail-heading">
          <h2 id="run-detail-heading">Run Detail</h2>
          <div className="stat-grid">
            {[
              runView.runStatus,
              runView.publicationStatus,
              runView.runTimestamp,
              runView.reportDate,
              runView.mode,
              runView.requestedBatchSize
            ].map((field) => (
              <div className="stat" key={field.label}>
                <span>{field.label}</span>
                <strong>{field.value}</strong>
              </div>
            ))}
          </div>

          <section className="detail-section" aria-labelledby="detail-summary-heading">
            <h3 id="detail-summary-heading">Summary</h3>
            <div className="summary-list">
              {runView.summaryFields.map((field) => (
                <div className="summary-row" key={field.label}>
                  <span>{field.label}</span>
                  <strong>{field.value}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="detail-section" aria-labelledby="detail-artifacts-heading">
            <h3 id="detail-artifacts-heading">Artifacts</h3>
            <ul className="artifact-list">
              {runView.artifacts.map((artifact) => (
                <li className="artifact-row" key={artifact.label}>
                  <span>
                    <strong>{artifact.label}</strong>
                    <small>{artifact.status}</small>
                  </span>
                  {artifact.available ? (
                    <a href={artifact.href}>{artifact.filename}</a>
                  ) : (
                    <em>Unavailable</em>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </section>
      </section>
    </main>
  );
}
