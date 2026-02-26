import { createClient } from "@supabase/supabase-js";
import type { Database } from "@/types/database.types";

// Service role client — ONLY use in server-side code, never expose to client
export function createAdminClient() {
  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  );
}
