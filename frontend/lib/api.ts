const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Campaign {
  id: string;
  name: string;
  creator_handle?: string;
  platform: string;
  payout_per_1k?: number;
  min_clip_length: number;
  max_clip_length: number;
  required_hashtags: string[];
  required_tags: string[];
  forbidden_topics: string[];
  style_notes?: string;
  created_at: string;
}

export interface Job {
  id: string;
  campaign_id?: string;
  source_type: string;
  source_url?: string;
  original_filename?: string;
  storage_path?: string;
  status: 'queued' | 'downloading' | 'transcribing' | 'analyzing' | 'rendering' | 'done' | 'failed' | 'cancelled';
  cancelled?: boolean;
  celery_task_id?: string;
  error_message?: string;
  transcript_path?: string;
  layout_style: 'full_bleed' | 'boxed';
  boxed_background_color: 'black' | 'white';
  created_at: string;
  updated_at: string;
}

export interface Clip {
  id: string;
  job_id: string;
  clip_index: number;
  start_time: number;
  end_time: number;
  hook?: string;
  category?: string;
  viral_score?: number;
  score_reason?: string;
  storage_path?: string;
  public_url?: string;
  views: number;
  earnings: number;
  created_at: string;
}

export async function getCampaigns(): Promise<Campaign[]> {
  const res = await fetch(`${API_URL}/campaigns/`);
  if (!res.ok) throw new Error('Failed to fetch campaigns');
  return res.json();
}

export async function createCampaign(data: Omit<Campaign, 'id' | 'created_at'>): Promise<Campaign> {
  const res = await fetch(`${API_URL}/campaigns/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create campaign');
  return res.json();
}

export async function updateCampaign(id: string, data: Partial<Campaign>): Promise<Campaign> {
  const res = await fetch(`${API_URL}/campaigns/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update campaign');
  return res.json();
}

export async function patchCampaign(
  id: string,
  data: Partial<Omit<Campaign, 'id' | 'created_at'>>
): Promise<Campaign> {
  const res = await fetch(`${API_URL}/campaigns/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update campaign');
  return res.json();
}

export async function deleteCampaign(id: string): Promise<void> {
  await fetch(`${API_URL}/campaigns/${id}`, { method: 'DELETE' });
}

export async function getJobs(): Promise<Job[]> {
  const res = await fetch(`${API_URL}/jobs/`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job');
  return res.json();
}

export async function createJobFromUrl(
  sourceUrl: string,
  campaignId?: string,
  layoutStyle: string = 'full_bleed',
  bgColor: string = 'black',
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('source_type', 'youtube_url');
  formData.append('source_url', sourceUrl);
  if (campaignId) formData.append('campaign_id', campaignId);
  formData.append('layout_style', layoutStyle);
  formData.append('boxed_background_color', bgColor);
  const res = await fetch(`${API_URL}/jobs/`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Failed to create job');
  return res.json();
}

export async function createJobFromFile(
  file: File,
  campaignId?: string
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('source_type', 'file_upload');
  formData.append('file', file);
  if (campaignId) formData.append('campaign_id', campaignId);
  const res = await fetch(`${API_URL}/jobs/`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Failed to create job');
  return res.json();
}

export async function createJobFromLocalPath(
  localPath: string,
  campaignId?: string,
  layoutStyle: string = 'full_bleed',
  bgColor: string = 'black',
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('source_type', 'local_path');
  formData.append('source_url', localPath);
  if (campaignId) formData.append('campaign_id', campaignId);
  formData.append('layout_style', layoutStyle);
  formData.append('boxed_background_color', bgColor);
  const res = await fetch(`${API_URL}/jobs/`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Failed to create job');
  return res.json();
}

export async function getClips(jobId: string): Promise<Clip[]> {
  const res = await fetch(`${API_URL}/clips/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch clips');
  return res.json();
}

export async function updateClip(
  clipId: string,
  data: { views?: number; earnings?: number }
): Promise<Clip> {
  const res = await fetch(`${API_URL}/clips/${clipId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update clip');
  return res.json();
}

export async function cancelJob(jobId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/jobs/${jobId}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to cancel job');
  return res.json();
}

export async function retryJob(jobId: string): Promise<{ status: string; job_id: string }> {
  const res = await fetch(`${API_URL}/jobs/${jobId}/retry`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to retry job' }));
    throw new Error(err.detail || 'Failed to retry job');
  }
  return res.json();
}

export async function deleteJob(jobId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/jobs/${jobId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete job');
  return res.json();
}
