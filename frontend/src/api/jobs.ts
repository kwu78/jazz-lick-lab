import { apiFetch, BASE_URL } from "./client";

/* ── Types ─────────────────────────────────────────── */

export interface Job {
  id: string;
  status: string;
  instrument: string;
  audio_path: string;
  created_at: string;
  result_json: Record<string, unknown> | null;
  error: string | null;
}

export interface Selection {
  selection_id: string;
  name: string;
  start_sec: number;
  end_sec: number;
  created_at: string;
}

export interface CoverageMetrics {
  total_notes: number;
  chord_tone_notes: number;
  tension_notes: number;
  other_notes: number;
  chord_tone_pct: number;
  tension_pct: number;
}

export interface IiVIEvent {
  start_sec: number;
  end_sec: number;
  chords: string[];
  key_guess: string | null;
}

export interface Analysis {
  job_id: string;
  selection_id: string;
  window_start_sec: number;
  window_end_sec: number;
  metrics: CoverageMetrics;
  ii_v_i: IiVIEvent[];
}

export interface Coaching {
  summary: string;
  why_it_works: string;
  practice_steps: string[];
  variation_idea: string;
  listening_tip: string;
  rationale: string | null;
  flags: string[];
}

export interface PracticePackArtifact {
  artifact_id: string;
  selection_id: string;
  keys_included: string[];
  zip_path: string;
  created_at: string;
}

export interface JobSettings {
  bpm: number | null;
  offset_sec: number;
  time_signature: string | null;
}

/* ── API calls ─────────────────────────────────────── */

export async function createJob(file: File, instrument?: string): Promise<Job> {
  const form = new FormData();
  form.append("audio", file);
  if (instrument) form.append("instrument", instrument);
  return apiFetch<Job>("/jobs", { method: "POST", body: form });
}

export async function getJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/jobs/${jobId}`);
}

export function getAudioUrl(jobId: string): string {
  return `${BASE_URL}/jobs/${jobId}/audio`;
}

export async function listSelections(
  jobId: string
): Promise<{ selections: Selection[] }> {
  return apiFetch(`/jobs/${jobId}/selection`);
}

export async function createSelection(
  jobId: string,
  data: { name?: string; start_sec: number; end_sec: number }
): Promise<{ job_id: string; selection: Selection }> {
  return apiFetch(`/jobs/${jobId}/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getAnalysis(
  jobId: string,
  selectionId: string
): Promise<Analysis> {
  return apiFetch(`/jobs/${jobId}/analysis?selection_id=${selectionId}`);
}

export async function getCoaching(
  jobId: string,
  selectionId: string
): Promise<Coaching> {
  return apiFetch(`/jobs/${jobId}/coaching?selection_id=${selectionId}`);
}

export async function createPracticePack(
  jobId: string,
  selectionId: string
): Promise<Record<string, unknown>> {
  return apiFetch(`/jobs/${jobId}/practice-pack`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selection_id: selectionId }),
  });
}

export async function listPracticePacks(
  jobId: string
): Promise<{ practice_packs: PracticePackArtifact[] }> {
  return apiFetch(`/jobs/${jobId}/practice-pack`);
}

export function downloadPracticePackUrl(
  jobId: string,
  artifactId: string
): string {
  return `${BASE_URL}/jobs/${jobId}/practice-pack/${artifactId}/download`;
}

export async function saveSettings(
  jobId: string,
  settings: Partial<JobSettings>
): Promise<JobSettings> {
  const res = await apiFetch<{ job_id: string; settings: JobSettings }>(
    `/jobs/${jobId}/settings`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    }
  );
  return res.settings;
}
