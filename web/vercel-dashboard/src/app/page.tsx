import {
  buildDailyEvidenceRunView,
  createDailyEvidenceRunRepository
} from "../lib/dailyEvidenceRuns";
import { requireAuthenticatedUser } from "../lib/auth";
import { requireSupabaseEnv } from "../lib/env";

export default async function DashboardPage() {
  const { supabase, user } = await requireAuthenticatedUser();
  const latestRun = await createDailyEvidenceRunRepository(supabase).getLatestRun();
  const runView = buildDailyEvidenceRunView(latestRun, requireSupabaseEnv().url);

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
            <h1>Nattome Daily Evidence Dashboard</h1>
            <p className="muted">
              Read-only view for cloud-published TikTok evidence runs.
            </p>
          </div>
          <span className="status-pill">Supabase Auth protected</span>
        </div>

        <div className="grid">
          <section className="panel" aria-labelledby="latest-run-heading">
            <h2 id="latest-run-heading">Latest Daily Evidence Run</h2>
            {runView.state === "available" ? (
              <>
                <p className="muted">
                  Latest published run {runView.runId} is ready for review.
                </p>
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
                <section className="detail-section" aria-labelledby="summary-heading">
                  <h3 id="summary-heading">Summary</h3>
                  <div className="summary-list">
                    {runView.summaryFields.map((field) => (
                      <div className="summary-row" key={field.label}>
                        <span>{field.label}</span>
                        <strong>{field.value}</strong>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="detail-section" aria-labelledby="artifacts-heading">
                  <h3 id="artifacts-heading">Daily Output Set</h3>
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
              </>
            ) : (
              <p className="empty">{runView.message}</p>
            )}
          </section>

          <aside className="panel" aria-labelledby="access-heading">
            <h2 id="access-heading">Access</h2>
            <p className="muted">
              Anonymous visitors are redirected to the login route before this
              dashboard renders.
            </p>
          </aside>
        </div>
      </section>
    </main>
  );
}
