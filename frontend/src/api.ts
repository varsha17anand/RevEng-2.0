/**
 * TruthLens API Client
 */

export interface SampleItem {
  id: string;
  filename: string;
  title: string;
  url: string;
  description: string;
}

export interface AnalyzeResponse {
  mode: 'instagram' | 'truthlens';
  label: string;
  has_ai_label: boolean;
  fraction: number;
  tiles_marked: number;
  total_tiles: number;
  global_z: number;
  heatmap_base64: string | null;
  provenance: 'verified' | 'tampered' | 'none';
  provenance_details: string;
  metadata_found: boolean;
  timings_ms: number;
}

export interface AttackResponse {
  attack: string;
  image_base64: string;
  format: string;
  size: [number, number];
}

export interface AttackLabRow {
  attack: string;
  attack_name: string;
  instagram_label: string;
  instagram_detected: boolean;
  truthlens_label: string;
  truthlens_detected: boolean;
  fraction_marked: number;
  tiles_marked: number;
  total_tiles: number;
  global_z: number;
  provenance_status: string;
}

export interface AttackLabResponse {
  rows: AttackLabRow[];
  total_attacks: number;
  timings_ms: number;
}

export interface StudioGenerateResponse {
  image_base64: string;
  manifest: any;
  label: string;
  tiles_marked: number;
  total_tiles: number;
}

export interface StudioEditResponse {
  image_base64: string;
  manifest: any;
  label: string;
  edited_tiles: [number, number][];
  fraction_edited: number;
}

const API_BASE = '/api';

export async function fetchSamples(): Promise<SampleItem[]> {
  const res = await fetch(`${API_BASE}/samples`);
  if (!res.ok) throw new Error('Failed to load sample images');
  return res.json();
}

export async function analyzeImage(
  imageBlob: Blob | File,
  mode: 'instagram' | 'truthlens'
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('file', imageBlob, 'image.png');
  formData.append('mode', mode);

  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
    throw new Error(err.detail || 'Analysis request failed');
  }
  return res.json();
}

export async function runAttack(
  imageBlob: Blob | File,
  attackName: string
): Promise<AttackResponse> {
  const formData = new FormData();
  formData.append('file', imageBlob, 'image.png');
  formData.append('attack', attackName);

  const res = await fetch(`${API_BASE}/attack`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Attack failed' }));
    throw new Error(err.detail || 'Attack request failed');
  }
  return res.json();
}

export async function runAttackLab(
  imageBlob: Blob | File
): Promise<AttackLabResponse> {
  const formData = new FormData();
  formData.append('file', imageBlob, 'image.png');

  const res = await fetch(`${API_BASE}/attack-lab`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Attack Lab failed' }));
    throw new Error(err.detail || 'Attack Lab request failed');
  }
  return res.json();
}

export async function studioGenerate(
  prompt: string,
  sampleId?: string,
  baseFile?: Blob | File
): Promise<StudioGenerateResponse> {
  const formData = new FormData();
  formData.append('prompt', prompt);
  if (sampleId) formData.append('sample_id', sampleId);
  if (baseFile) formData.append('file', baseFile, 'base.png');

  const res = await fetch(`${API_BASE}/studio/generate`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Studio generation failed' }));
    throw new Error(err.detail || 'Generation request failed');
  }
  return res.json();
}

export async function studioEdit(
  imageBlob: Blob | File,
  box: { x1: number; y1: number; x2: number; y2: number },
  style: string = 'cyberpunk'
): Promise<StudioEditResponse> {
  const formData = new FormData();
  formData.append('file', imageBlob, 'image.png');
  formData.append('x1', Math.round(box.x1).toString());
  formData.append('y1', Math.round(box.y1).toString());
  formData.append('x2', Math.round(box.x2).toString());
  formData.append('y2', Math.round(box.y2).toString());
  formData.append('style', style);

  const res = await fetch(`${API_BASE}/studio/edit`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Studio edit failed' }));
    throw new Error(err.detail || 'Edit request failed');
  }
  return res.json();
}

export async function urlToBlob(url: string): Promise<Blob> {
  const res = await fetch(url);
  return res.blob();
}
