import { createDailyEvidenceRunRepository } from "../lib/dailyEvidenceRuns";
import { requireAuthenticatedUser } from "../lib/auth";

export default async function DashboardPage() {
  const { supabase, user } = await requireAuthenticatedUser();
  const latestRun = await createDailyEvidenceRunRepository(supabase).getLatestRun();

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
            {latestRun ? (
              <>
                <p className="muted">
                  Latest published run metadata is available. Detailed artifact links are
                  added in the next dashboard slice.
                </p>
                <div className="stat-grid">
                  <div className="stat">
                    <span>Run status</span>
                    <strong>{latestRun.status}</strong>
                  </div>
                  <div className="stat">
                    <span>Publication</span>
                    <strong>{latestRun.publication_status}</strong>
                  </div>
                  <div className="stat">
                    <span>Report date</span>
                    <strong>{latestRun.report_date}</strong>
                  </div>
                  <div className="stat">
                    <span>Mode</span>
                    <strong>{latestRun.mode}</strong>
                  </div>
                </div>
              </>
            ) : (
              <p className="empty">
                No cloud-published Daily Evidence Run is available yet.
              </p>
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
