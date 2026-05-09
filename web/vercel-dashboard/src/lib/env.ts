export type SupabaseBrowserEnv = {
  url: string;
  anonKey: string;
};

export function requireSupabaseEnv(): SupabaseBrowserEnv {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const missing = [
    ["NEXT_PUBLIC_SUPABASE_URL", url],
    ["NEXT_PUBLIC_SUPABASE_ANON_KEY", anonKey]
  ]
    .filter(([, value]) => !value)
    .map(([name]) => name);

  if (missing.length > 0) {
    throw new Error(
      `Missing required Vercel Supabase environment variables: ${missing.join(", ")}`
    );
  }

  return { url, anonKey } as SupabaseBrowserEnv;
}
