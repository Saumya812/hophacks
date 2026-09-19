import { table, t } from 'spacetimedb/server';

export const users = table({ name: "users" }, {
  id: t.string().primaryKey(),
  email: t.string(),
  role: t.string(),
  created_at: t.string(),
});

export const persons = table({ name: "persons" }, {
  id: t.string().primaryKey(),
  name: t.string(),
  age: t.i32(),
  gender: t.string().optional(),
  last_seen_location: t.string(),
  last_seen_date: t.string(),
  description: t.string(),
  photo_url: t.string().optional(),
  status: t.string().index('btree'),
  police_report_number: t.string().optional(),
  created_at: t.string(),
  ai_summary: t.string().optional(),
  ai_summary_updated_at: t.string().optional(),
  verified_police_report: t.bool(),
  last_verified_at: t.string().optional(),
  found_at: t.string().optional(),
  found_message: t.string().optional(),
  watchers_count: t.i32(),
  shares_count: t.i32(),
  tips_count: t.i32(),
  suspicious_flags: t.i32(),
  under_review: t.bool(),
  demo_tag: t.string().optional(),
  owner_token: t.string().optional(),
  contact_email: t.string().optional(),
  last_seen_time: t.string().optional(),
  source_listing_url: t.string().optional(),
  source_agency_name: t.string().optional(),
  external_case_number: t.string().optional(),
  source_last_checked_at: t.string().optional(),
  found_date: t.string().optional(),
  found_notes: t.string().optional(),
  verified_by: t.string().optional(),
});

export const sightings = table({ name: "sightings" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  location_lat: t.f64(),
  location_lng: t.f64(),
  date_time: t.string(),
  description: t.string(),
  confidence_level: t.i32(),
  submitter_email: t.string().optional(),
  created_at: t.string(),
  credibility_score: t.i32().optional(),
  family_review_flag: t.bool(),
  credibility_reasons: t.string().optional(),
  tip_type: t.string().optional(),
});

export const case_updates = table({ name: "case_updates" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  author_email: t.string().optional(),
  body: t.string(),
  created_at: t.string(),
});

export const case_coordinators = table({ name: "case_coordinators" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  email: t.string(),
  role: t.string(),
  created_at: t.string(),
});

export const alert_subscriptions = table({ name: "alert_subscriptions", indexes: [{ accessor: "person_id", algorithm: "btree", columns: ["person_id"] }] }, {
  id: t.string().primaryKey(),
  kind: t.string(),
  email: t.string(),
  query_text: t.string().optional(),
  zip_code: t.string().optional(),
  person_id: t.string().optional(),
  active: t.bool(),
  created_at: t.string(),
});

export const tip_clusters = table({ name: "tip_clusters" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  center_lat: t.f64(),
  center_lng: t.f64(),
  radius_km: t.f64(),
  tip_count: t.i32(),
  window_start: t.string(),
  window_end: t.string(),
  label: t.string().optional(),
  notified: t.bool(),
  created_at: t.string(),
});

export const profile_flags = table({ name: "profile_flags" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  reason: t.string().optional(),
  reporter_ip: t.string().optional(),
  created_at: t.string(),
});

export const search_memory = table({ name: "search_memory" }, {
  id: t.string().primaryKey(),
  participant_key: t.string().index('btree'),
  city: t.string().optional(),
  date_from: t.string().optional(),
  date_to: t.string().optional(),
  filters_json: t.string().optional(),
  updated_at: t.string(),
});

export const email_outbox_log = table({ name: "email_outbox_log" }, {
  id: t.string().primaryKey(),
  to_email: t.string(),
  subject: t.string(),
  body: t.string(),
  kind: t.string().optional(),
  meta: t.string().optional(),
  created_at: t.string(),
});

export const live_tip_events = table({ name: "live_tip_events", indexes: [{ accessor: "person_id", algorithm: "btree", columns: ["person_id"] }] }, {
  id: t.string().primaryKey(),
  person_id: t.string().optional(),
  person_name: t.string().optional(),
  snippet: t.string().optional(),
  created_at: t.string(),
});

export const case_source_links = table({ name: "case_source_links" }, {
  id: t.string().primaryKey(),
  person_id: t.string().index('btree'),
  title: t.string(),
  url: t.string(),
  source_type: t.string(),
  published_at: t.string().optional(),
  created_at: t.string(),
});

export const appTables = { users, persons, sightings, case_updates, case_coordinators, alert_subscriptions, tip_clusters, profile_flags, search_memory, email_outbox_log, live_tip_events, case_source_links };
