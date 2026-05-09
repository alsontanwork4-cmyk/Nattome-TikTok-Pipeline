export default function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-heading">
        <h1 id="login-heading">Nattome Dashboard Access</h1>
        <p className="muted">
          Supabase Auth is required before viewing the private Daily Evidence Run
          dashboard.
        </p>
      </section>
    </main>
  );
}
