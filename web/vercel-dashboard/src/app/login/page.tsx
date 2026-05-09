import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "../../lib/supabaseServer";

type LoginPageProps = {
  searchParams?: Promise<{
    error?: string;
    redirectedFrom?: string;
  }>;
};

async function signIn(formData: FormData) {
  "use server";

  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const redirectedFrom = String(formData.get("redirectedFrom") ?? "/");
  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithPassword({
    email,
    password
  });

  if (error) {
    redirect("/login?error=Invalid%20email%20or%20password");
  }

  redirect(redirectedFrom.startsWith("/") ? redirectedFrom : "/");
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = (await searchParams) ?? {};

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-heading">
        <h1 id="login-heading">Nattome Dashboard Access</h1>
        <p className="muted">
          Supabase Auth is required before viewing the private Daily Evidence Run
          dashboard.
        </p>
        <form className="login-form" action={signIn}>
          <input
            name="redirectedFrom"
            type="hidden"
            value={params.redirectedFrom ?? "/"}
          />
          <label>
            Email
            <input
              autoComplete="email"
              name="email"
              required
              type="email"
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              name="password"
              required
              type="password"
            />
          </label>
          {params.error ? <p className="form-error">{params.error}</p> : null}
          <button type="submit">Sign in</button>
        </form>
      </section>
    </main>
  );
}
