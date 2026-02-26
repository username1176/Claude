"use client";

import { useRef } from "react";
import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "@/types/database.types";

// Lazy ref — client is only created on first .current access in browser
export function useSupabase() {
  const clientRef = useRef<SupabaseClient<Database> | null>(null);

  if (typeof window !== "undefined" && !clientRef.current) {
    clientRef.current = createBrowserClient<Database>(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }

  return clientRef.current!;
}
