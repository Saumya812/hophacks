/**
 * Optional Supabase browser client for Realtime tip / status feeds.
 * When VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY are unset, exports null
 * and callers fall back to API polling — existing FastAPI flow unchanged.
 */
import { createClient } from '@supabase/supabase-js'

const url = (import.meta.env.VITE_SUPABASE_URL || '').trim()
const anon = (import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim()

export const supabase =
  url && anon
    ? createClient(url, anon, {
        realtime: { params: { eventsPerSecond: 4 } },
      })
    : null

export const supabaseRealtimeEnabled = Boolean(supabase)
