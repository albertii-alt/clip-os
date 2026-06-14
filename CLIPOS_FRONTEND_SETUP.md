# ClipOS — Frontend Setup Guide
> **Agent Instructions:** This is the complete frontend spec for ClipOS. Read this file AND `CLIPOS_PROJECT.md` fully before writing any code. Build components exactly as described. Use only the packages already installed. Do not add new dependencies without user approval.

---

## 1. Tech Stack (Already Installed)

| Layer | Package | Notes |
|---|---|---|
| Framework | Next.js 14+ (App Router) | TypeScript strict mode ON |
| Styling | Tailwind CSS v4 | No CSS modules |
| UI Components | shadcn/ui (Radix, Nova preset) | Use existing `components/ui/` |
| Animations | Framer Motion | Minimal, purposeful only |
| State | Zustand | Global job/clip state |
| HTTP | Native fetch + SWR | For polling job status |

**Install these additional packages before building:**
```bash
cd frontend
npm install swr zustand framer-motion
npx shadcn@latest add card badge progress table toast separator
```

---

## 2. Design System

**Theme:** Dark minimal dev-tool aesthetic
**Accent color:** `#4ADE80` (terminal green)
**Background:** `#0a0a0a` (near black)
**Surface:** `#111111` (dark card)
**Border:** `#222222`
**Text primary:** `#ffffff`
**Text muted:** `#666666`

Add these CSS variables to `app/globals.css` under `:root`:
```css
:root {
  --accent: #4ADE80;
  --bg: #0a0a0a;
  --surface: #111111;
  --border: #222222;
  --text: #ffffff;
  --muted: #666666;
}

body {
  background-color: var(--bg);
  color: var(--text);
}
```

---

## 3. Environment Variables

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://smxtocoqubexrbfejoed.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key_here
```

> Get the anon key from Supabase Dashboard → Settings → API Keys → Publishable key (the `sb_publishable_...` one).

---

## 4. Folder Structure

```
frontend/
├── app/
│   ├── layout.tsx                  # Root layout with sidebar
│   ├── page.tsx                    # Redirect to /dashboard
│   ├── globals.css                 # Global styles + CSS vars
│   ├── dashboard/
│   │   └── page.tsx                # Job list + stats overview
│   ├── upload/
│   │   └── page.tsx                # Upload form + YouTube URL input
│   ├── campaigns/
│   │   └── page.tsx                # Campaign CRUD manager
│   └── clips/
│       └── [jobId]/
│           └── page.tsx            # Clip preview + download for a job
├── components/
│   ├── ui/                         # shadcn/ui components (already exists)
│   ├── layout/
│   │   ├── Sidebar.tsx             # Left navigation sidebar
│   │   └── TopBar.tsx              # Top bar with page title
│   ├── dashboard/
│   │   ├── JobCard.tsx             # Single job card with status
│   │   ├── JobList.tsx             # List of all jobs
│   │   └── StatsBar.tsx            # Quick stats (total jobs, clips, earnings)
│   ├── upload/
│   │   ├── UploadForm.tsx          # YouTube URL + file upload form
│   │   └── JobStatusTracker.tsx    # Real-time job status polling
│   ├── campaigns/
│   │   ├── CampaignCard.tsx        # Single campaign display card
│   │   ├── CampaignForm.tsx        # Create/edit campaign form
│   │   └── CampaignList.tsx        # List of all campaigns
│   └── clips/
│       ├── ClipCard.tsx            # Single clip with preview + download
│       ├── ClipGrid.tsx            # Grid of clips for a job
│       └── EarningsInput.tsx       # Manual views/earnings input per clip
├── lib/
│   ├── api.ts                      # All API call functions
│   └── utils.ts                    # Already exists (shadcn)
└── stores/
    └── jobStore.ts                 # Zustand store
```

---

## 5. API Client (`lib/api.ts`)

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────
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
  status: 'queued' | 'downloading' | 'transcribing' | 'analyzing' | 'rendering' | 'done' | 'failed';
  error_message?: string;
  transcript_path?: string;
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

// ── Campaigns ──────────────────────────────────────────────
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

export async function deleteCampaign(id: string): Promise<void> {
  await fetch(`${API_URL}/campaigns/${id}`, { method: 'DELETE' });
}

// ── Jobs ───────────────────────────────────────────────────
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
  campaignId?: string
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('source_type', 'youtube_url');
  formData.append('source_url', sourceUrl);
  if (campaignId) formData.append('campaign_id', campaignId);

  const res = await fetch(`${API_URL}/jobs/`, {
    method: 'POST',
    body: formData,
  });
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

  const res = await fetch(`${API_URL}/jobs/`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to create job');
  return res.json();
}

// ── Clips ──────────────────────────────────────────────────
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
```

---

## 6. Zustand Store (`stores/jobStore.ts`)

```typescript
import { create } from 'zustand';
import { Job, Clip } from '@/lib/api';

interface JobStore {
  activeJobId: string | null;
  jobs: Job[];
  clips: Record<string, Clip[]>;
  setActiveJobId: (id: string | null) => void;
  setJobs: (jobs: Job[]) => void;
  setClips: (jobId: string, clips: Clip[]) => void;
  updateJob: (job: Job) => void;
}

export const useJobStore = create<JobStore>((set) => ({
  activeJobId: null,
  jobs: [],
  clips: {},
  setActiveJobId: (id) => set({ activeJobId: id }),
  setJobs: (jobs) => set({ jobs }),
  setClips: (jobId, clips) =>
    set((state) => ({ clips: { ...state.clips, [jobId]: clips } })),
  updateJob: (job) =>
    set((state) => ({
      jobs: state.jobs.map((j) => (j.id === job.id ? job : j)),
    })),
}));
```

---

## 7. Root Layout (`app/layout.tsx`)

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/layout/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'ClipOS',
  description: 'AI-powered Whop clipping automation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ background: 'var(--bg)' }}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

---

## 8. Sidebar (`components/layout/Sidebar.tsx`)

```typescript
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Upload, Megaphone, Scissors } from 'lucide-react';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/upload', label: 'New Job', icon: Upload },
  { href: '/campaigns', label: 'Campaigns', icon: Megaphone },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-56 h-screen flex flex-col border-r"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      {/* Logo */}
      <div className="p-5 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Scissors size={20} style={{ color: 'var(--accent)' }} />
          <span className="font-bold text-lg tracking-tight">ClipOS</span>
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
          Whop Clipping Automation
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors"
              style={{
                background: active ? 'rgba(74, 222, 128, 0.1)' : 'transparent',
                color: active ? 'var(--accent)' : 'var(--muted)',
              }}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t" style={{ borderColor: 'var(--border)' }}>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          Phase 1 — Local Build
        </p>
      </div>
    </aside>
  );
}
```

---

## 9. Home Page Redirect (`app/page.tsx`)

```typescript
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/dashboard');
}
```

---

## 10. Dashboard Page (`app/dashboard/page.tsx`)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getJobs, getClips, Job, Clip } from '@/lib/api';
import JobList from '@/components/dashboard/JobList';
import StatsBar from '@/components/dashboard/StatsBar';

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [allClips, setAllClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const jobsData = await getJobs();
        setJobs(jobsData);

        const doneJobs = jobsData.filter((j) => j.status === 'done');
        const clipsArrays = await Promise.all(
          doneJobs.map((j) => getClips(j.id))
        );
        setAllClips(clipsArrays.flat());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totalEarnings = allClips.reduce((sum, c) => sum + (c.earnings || 0), 0);
  const totalViews = allClips.reduce((sum, c) => sum + (c.views || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
          Your clipping operation overview
        </p>
      </div>

      <StatsBar
        totalJobs={jobs.length}
        totalClips={allClips.length}
        totalViews={totalViews}
        totalEarnings={totalEarnings}
      />

      <div>
        <h2 className="text-lg font-semibold mb-3">Recent Jobs</h2>
        {loading ? (
          <p style={{ color: 'var(--muted)' }}>Loading...</p>
        ) : (
          <JobList jobs={jobs} />
        )}
      </div>
    </div>
  );
}
```

---

## 11. StatsBar (`components/dashboard/StatsBar.tsx`)

```typescript
interface StatsBarProps {
  totalJobs: number;
  totalClips: number;
  totalViews: number;
  totalEarnings: number;
}

export default function StatsBar({
  totalJobs,
  totalClips,
  totalViews,
  totalEarnings,
}: StatsBarProps) {
  const stats = [
    { label: 'Total Jobs', value: totalJobs },
    { label: 'Clips Generated', value: totalClips },
    { label: 'Total Views', value: totalViews.toLocaleString() },
    { label: 'Earnings', value: `$${totalEarnings.toFixed(2)}` },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(({ label, value }) => (
        <div
          key={label}
          className="rounded-lg p-4 border"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
        >
          <p className="text-xs" style={{ color: 'var(--muted)' }}>
            {label}
          </p>
          <p
            className="text-2xl font-bold mt-1"
            style={{ color: 'var(--accent)' }}
          >
            {value}
          </p>
        </div>
      ))}
    </div>
  );
}
```

---

## 12. JobCard (`components/dashboard/JobCard.tsx`)

```typescript
'use client';

import Link from 'next/link';
import { Job } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  queued: '#666666',
  downloading: '#f59e0b',
  transcribing: '#3b82f6',
  analyzing: '#8b5cf6',
  rendering: '#f97316',
  done: '#4ADE80',
  failed: '#ef4444',
};

export default function JobCard({ job }: { job: Job }) {
  const color = STATUS_COLORS[job.status] || '#666666';
  const date = new Date(job.created_at).toLocaleDateString();

  return (
    <div
      className="rounded-lg border p-4 flex items-center justify-between hover:border-green-400 transition-colors"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="space-y-1">
        <p className="text-sm font-medium truncate max-w-xs">
          {job.original_filename || job.source_url || job.id}
        </p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {date}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <span
          className="text-xs font-medium px-2 py-1 rounded-full"
          style={{ background: `${color}20`, color }}
        >
          {job.status}
        </span>

        {job.status === 'done' && (
          <Link
            href={`/clips/${job.id}`}
            className="text-xs px-3 py-1 rounded-md font-medium transition-colors"
            style={{ background: 'var(--accent)', color: '#000' }}
          >
            View Clips
          </Link>
        )}
      </div>
    </div>
  );
}
```

---

## 13. JobList (`components/dashboard/JobList.tsx`)

```typescript
import { Job } from '@/lib/api';
import JobCard from './JobCard';

export default function JobList({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0) {
    return (
      <div
        className="rounded-lg border p-8 text-center"
        style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}
      >
        <p>No jobs yet. Create your first job in New Job.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
```

---

## 14. Upload Page (`app/upload/page.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import UploadForm from '@/components/upload/UploadForm';
import JobStatusTracker from '@/components/upload/JobStatusTracker';

export default function UploadPage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const router = useRouter();

  function handleJobCreated(id: string) {
    setJobId(id);
  }

  function handleJobDone(id: string) {
    router.push(`/clips/${id}`);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Job</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
          Submit a YouTube URL or upload a video file to generate clips
        </p>
      </div>

      {!jobId ? (
        <UploadForm onJobCreated={handleJobCreated} />
      ) : (
        <JobStatusTracker jobId={jobId} onDone={handleJobDone} />
      )}
    </div>
  );
}
```

---

## 15. UploadForm (`components/upload/UploadForm.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { getCampaigns, createJobFromUrl, createJobFromFile, Campaign } from '@/lib/api';
import { useEffect } from 'react';

interface UploadFormProps {
  onJobCreated: (jobId: string) => void;
}

export default function UploadForm({ onJobCreated }: UploadFormProps) {
  const [mode, setMode] = useState<'url' | 'file'>('url');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [campaignId, setCampaignId] = useState('');
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getCampaigns().then(setCampaigns).catch(() => {});
  }, []);

  async function handleSubmit() {
    setError('');
    setLoading(true);
    try {
      let result;
      if (mode === 'url') {
        if (!url) throw new Error('Please enter a YouTube URL');
        result = await createJobFromUrl(url, campaignId || undefined);
      } else {
        if (!file) throw new Error('Please select a file');
        result = await createJobFromFile(file, campaignId || undefined);
      }
      onJobCreated(result.job_id);
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="rounded-lg border p-6 space-y-5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      {/* Mode Toggle */}
      <div className="flex gap-2">
        {(['url', 'file'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
            style={{
              background: mode === m ? 'var(--accent)' : 'transparent',
              color: mode === m ? '#000' : 'var(--muted)',
              border: `1px solid ${mode === m ? 'var(--accent)' : 'var(--border)'}`,
            }}
          >
            {m === 'url' ? 'YouTube URL' : 'File Upload'}
          </button>
        ))}
      </div>

      {/* Input */}
      {mode === 'url' ? (
        <div className="space-y-2">
          <label className="text-sm" style={{ color: 'var(--muted)' }}>
            YouTube URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full px-3 py-2 rounded-md text-sm outline-none"
            style={{
              background: '#1a1a1a',
              border: '1px solid var(--border)',
              color: 'var(--text)',
            }}
          />
        </div>
      ) : (
        <div className="space-y-2">
          <label className="text-sm" style={{ color: 'var(--muted)' }}>
            Video File
          </label>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full text-sm"
            style={{ color: 'var(--muted)' }}
          />
        </div>
      )}

      {/* Campaign Select */}
      <div className="space-y-2">
        <label className="text-sm" style={{ color: 'var(--muted)' }}>
          Campaign (optional)
        </label>
        <select
          value={campaignId}
          onChange={(e) => setCampaignId(e.target.value)}
          className="w-full px-3 py-2 rounded-md text-sm outline-none"
          style={{
            background: '#1a1a1a',
            border: '1px solid var(--border)',
            color: 'var(--text)',
          }}
        >
          <option value="">No campaign</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} — {c.platform}
            </option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm" style={{ color: '#ef4444' }}>
          {error}
        </p>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-2 rounded-md text-sm font-medium transition-opacity"
        style={{
          background: 'var(--accent)',
          color: '#000',
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? 'Submitting...' : 'Generate Clips'}
      </button>
    </div>
  );
}
```

---

## 16. JobStatusTracker (`components/upload/JobStatusTracker.tsx`)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getJob, Job } from '@/lib/api';

const STEPS = ['queued', 'downloading', 'transcribing', 'analyzing', 'rendering', 'done'];

interface JobStatusTrackerProps {
  jobId: string;
  onDone: (jobId: string) => void;
}

export default function JobStatusTracker({ jobId, onDone }: JobStatusTrackerProps) {
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getJob(jobId);
        setJob(data);
        if (data.status === 'done') {
          onDone(jobId);
          return;
        }
        if (data.status === 'failed') return;
      } catch {}
    };

    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [jobId]);

  if (!job) return <p style={{ color: 'var(--muted)' }}>Starting job...</p>;

  const currentStep = STEPS.indexOf(job.status);

  return (
    <div
      className="rounded-lg border p-6 space-y-5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div>
        <h2 className="text-lg font-semibold">Processing Job</h2>
        <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
          Job ID: {jobId}
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {STEPS.filter((s) => s !== 'done').map((step, idx) => {
          const done = currentStep > idx;
          const active = currentStep === idx;
          return (
            <div key={step} className="flex items-center gap-3">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: done
                    ? 'var(--accent)'
                    : active
                    ? '#f59e0b'
                    : 'var(--border)',
                }}
              />
              <span
                className="text-sm capitalize"
                style={{
                  color: done
                    ? 'var(--accent)'
                    : active
                    ? '#f59e0b'
                    : 'var(--muted)',
                }}
              >
                {step}
              </span>
              {active && (
                <span className="text-xs animate-pulse" style={{ color: '#f59e0b' }}>
                  in progress...
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Failed state */}
      {job.status === 'failed' && (
        <div
          className="rounded-md p-3 text-sm"
          style={{ background: '#ef444420', color: '#ef4444' }}
        >
          <p className="font-medium">Job failed</p>
          <p className="text-xs mt-1">{job.error_message}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 17. Clips Page (`app/clips/[jobId]/page.tsx`)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getClips, Clip } from '@/lib/api';
import ClipGrid from '@/components/clips/ClipGrid';

export default function ClipsPage({ params }: { params: { jobId: string } }) {
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getClips(params.jobId)
      .then(setClips)
      .finally(() => setLoading(false));
  }, [params.jobId]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Clips</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
          Job ID: {params.jobId}
        </p>
      </div>

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading clips...</p>
      ) : (
        <ClipGrid clips={clips} />
      )}
    </div>
  );
}
```

---

## 18. ClipCard (`components/clips/ClipCard.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { Clip, updateClip } from '@/lib/api';

export default function ClipCard({ clip }: { clip: Clip }) {
  const [views, setViews] = useState(clip.views || 0);
  const [earnings, setEarnings] = useState(clip.earnings || 0);
  const [saving, setSaving] = useState(false);

  const duration = (clip.end_time - clip.start_time).toFixed(0);

  async function handleSave() {
    setSaving(true);
    try {
      await updateClip(clip.id, { views, earnings });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="rounded-lg border p-4 space-y-3"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Clip #{clip.clip_index}</span>
        <span
          className="text-xs px-2 py-1 rounded-full font-medium"
          style={{ background: 'rgba(74,222,128,0.1)', color: 'var(--accent)' }}
        >
          Score: {clip.viral_score ?? '—'}
        </span>
      </div>

      {/* Hook */}
      {clip.hook && (
        <p className="text-sm italic" style={{ color: 'var(--muted)' }}>
          "{clip.hook}"
        </p>
      )}

      {/* Meta */}
      <div className="flex gap-4 text-xs" style={{ color: 'var(--muted)' }}>
        <span>{duration}s</span>
        <span className="capitalize">{clip.category?.replace('_', ' ')}</span>
      </div>

      {/* Reason */}
      {clip.score_reason && (
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {clip.score_reason}
        </p>
      )}

      {/* Video Preview */}
      {clip.public_url && (
        <video
          src={clip.public_url}
          controls
          className="w-full rounded-md"
          style={{ maxHeight: '300px' }}
        />
      )}

      {/* Download */}
      {clip.public_url && (
        <a
          href={clip.public_url}
          download
          className="block text-center py-2 rounded-md text-sm font-medium"
          style={{ background: 'var(--accent)', color: '#000' }}
        >
          Download
        </a>
      )}

      {/* Earnings Tracker */}
      <div className="border-t pt-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
        <p className="text-xs font-medium" style={{ color: 'var(--muted)' }}>
          Track Performance
        </p>
        <div className="flex gap-2">
          <input
            type="number"
            value={views}
            onChange={(e) => setViews(Number(e.target.value))}
            placeholder="Views"
            className="flex-1 px-2 py-1 rounded text-xs outline-none"
            style={{
              background: '#1a1a1a',
              border: '1px solid var(--border)',
              color: 'var(--text)',
            }}
          />
          <input
            type="number"
            value={earnings}
            onChange={(e) => setEarnings(Number(e.target.value))}
            placeholder="Earnings $"
            className="flex-1 px-2 py-1 rounded text-xs outline-none"
            style={{
              background: '#1a1a1a',
              border: '1px solid var(--border)',
              color: 'var(--text)',
            }}
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 rounded text-xs font-medium"
            style={{ background: 'var(--accent)', color: '#000' }}
          >
            {saving ? '...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 19. ClipGrid (`components/clips/ClipGrid.tsx`)

```typescript
import { Clip } from '@/lib/api';
import ClipCard from './ClipCard';

export default function ClipGrid({ clips }: { clips: Clip[] }) {
  if (clips.length === 0) {
    return (
      <p style={{ color: 'var(--muted)' }}>
        No clips found for this job.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {clips.map((clip) => (
        <ClipCard key={clip.id} clip={clip} />
      ))}
    </div>
  );
}
```

---

## 20. Campaigns Page (`app/campaigns/page.tsx`)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getCampaigns, createCampaign, deleteCampaign, Campaign } from '@/lib/api';
import CampaignList from '@/components/campaigns/CampaignList';
import CampaignForm from '@/components/campaigns/CampaignForm';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    const data = await getCampaigns();
    setCampaigns(data);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(data: Omit<Campaign, 'id' | 'created_at'>) {
    await createCampaign(data);
    setShowForm(false);
    load();
  }

  async function handleDelete(id: string) {
    await deleteCampaign(id);
    load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Campaigns</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
            Manage your Whop clipping campaigns
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-md text-sm font-medium"
          style={{ background: 'var(--accent)', color: '#000' }}
        >
          {showForm ? 'Cancel' : '+ New Campaign'}
        </button>
      </div>

      {showForm && (
        <CampaignForm onSubmit={handleCreate} />
      )}

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading...</p>
      ) : (
        <CampaignList campaigns={campaigns} onDelete={handleDelete} />
      )}
    </div>
  );
}
```

---

## 21. CampaignForm (`components/campaigns/CampaignForm.tsx`)

```typescript
'use client';

import { useState } from 'react';
import { Campaign } from '@/lib/api';

interface CampaignFormProps {
  onSubmit: (data: Omit<Campaign, 'id' | 'created_at'>) => void;
  initial?: Partial<Campaign>;
}

export default function CampaignForm({ onSubmit, initial }: CampaignFormProps) {
  const [name, setName] = useState(initial?.name || '');
  const [handle, setHandle] = useState(initial?.creator_handle || '');
  const [platform, setPlatform] = useState(initial?.platform || 'tiktok');
  const [payout, setPayout] = useState(initial?.payout_per_1k || 5);
  const [minLen, setMinLen] = useState(initial?.min_clip_length || 30);
  const [maxLen, setMaxLen] = useState(initial?.max_clip_length || 60);
  const [hashtags, setHashtags] = useState(initial?.required_hashtags?.join(', ') || '');
  const [tags, setTags] = useState(initial?.required_tags?.join(', ') || '');
  const [forbidden, setForbidden] = useState(initial?.forbidden_topics?.join(', ') || '');
  const [styleNotes, setStyleNotes] = useState(initial?.style_notes || '');

  function handleSubmit() {
    onSubmit({
      name,
      creator_handle: handle,
      platform,
      payout_per_1k: payout,
      min_clip_length: minLen,
      max_clip_length: maxLen,
      required_hashtags: hashtags.split(',').map((s) => s.trim()).filter(Boolean),
      required_tags: tags.split(',').map((s) => s.trim()).filter(Boolean),
      forbidden_topics: forbidden.split(',').map((s) => s.trim()).filter(Boolean),
      style_notes: styleNotes,
    });
  }

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid var(--border)',
    color: 'var(--text)',
  };

  const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="space-y-1">
      <label className="text-xs" style={{ color: 'var(--muted)' }}>{label}</label>
      {children}
    </div>
  );

  return (
    <div
      className="rounded-lg border p-5 space-y-4"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="grid grid-cols-2 gap-4">
        <Field label="Campaign Name">
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
        </Field>
        <Field label="Creator Handle">
          <input value={handle} onChange={(e) => setHandle(e.target.value)}
            placeholder="@creator" className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
        </Field>
        <Field label="Platform">
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle}>
            <option value="tiktok">TikTok</option>
            <option value="youtube_shorts">YouTube Shorts</option>
            <option value="instagram_reels">Instagram Reels</option>
          </select>
        </Field>
        <Field label="Payout per 1K views ($)">
          <input type="number" value={payout} onChange={(e) => setPayout(Number(e.target.value))}
            className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
        </Field>
        <Field label="Min Clip Length (s)">
          <input type="number" value={minLen} onChange={(e) => setMinLen(Number(e.target.value))}
            className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
        </Field>
        <Field label="Max Clip Length (s)">
          <input type="number" value={maxLen} onChange={(e) => setMaxLen(Number(e.target.value))}
            className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
        </Field>
      </div>
      <Field label="Required Hashtags (comma separated)">
        <input value={hashtags} onChange={(e) => setHashtags(e.target.value)}
          placeholder="#clips, #podcast" className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
      </Field>
      <Field label="Required Tags (comma separated)">
        <input value={tags} onChange={(e) => setTags(e.target.value)}
          placeholder="@creator" className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
      </Field>
      <Field label="Forbidden Topics (comma separated)">
        <input value={forbidden} onChange={(e) => setForbidden(e.target.value)}
          placeholder="politics, competitors" className="w-full px-3 py-2 rounded text-sm outline-none" style={inputStyle} />
      </Field>
      <Field label="Style Notes">
        <textarea value={styleNotes} onChange={(e) => setStyleNotes(e.target.value)}
          rows={2} placeholder="Focus on emotional moments..."
          className="w-full px-3 py-2 rounded text-sm outline-none resize-none" style={inputStyle} />
      </Field>
      <button onClick={handleSubmit}
        className="w-full py-2 rounded text-sm font-medium"
        style={{ background: 'var(--accent)', color: '#000' }}>
        Save Campaign
      </button>
    </div>
  );
}
```

---

## 22. CampaignCard + CampaignList (`components/campaigns/CampaignCard.tsx` and `CampaignList.tsx`)

**CampaignCard.tsx:**
```typescript
import { Campaign } from '@/lib/api';

interface CampaignCardProps {
  campaign: Campaign;
  onDelete: (id: string) => void;
}

export default function CampaignCard({ campaign, onDelete }: CampaignCardProps) {
  return (
    <div
      className="rounded-lg border p-4 space-y-2"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">{campaign.name}</p>
        <button
          onClick={() => onDelete(campaign.id)}
          className="text-xs px-2 py-1 rounded"
          style={{ background: '#ef444420', color: '#ef4444' }}
        >
          Delete
        </button>
      </div>
      <div className="flex gap-3 text-xs" style={{ color: 'var(--muted)' }}>
        <span className="capitalize">{campaign.platform}</span>
        <span>${campaign.payout_per_1k}/1K views</span>
        <span>{campaign.min_clip_length}s – {campaign.max_clip_length}s</span>
      </div>
      {campaign.required_hashtags.length > 0 && (
        <p className="text-xs" style={{ color: 'var(--accent)' }}>
          {campaign.required_hashtags.join(' ')}
        </p>
      )}
    </div>
  );
}
```

**CampaignList.tsx:**
```typescript
import { Campaign } from '@/lib/api';
import CampaignCard from './CampaignCard';

interface CampaignListProps {
  campaigns: Campaign[];
  onDelete: (id: string) => void;
}

export default function CampaignList({ campaigns, onDelete }: CampaignListProps) {
  if (campaigns.length === 0) {
    return (
      <p style={{ color: 'var(--muted)' }}>
        No campaigns yet. Create one to attach rules to your jobs.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {campaigns.map((c) => (
        <CampaignCard key={c.id} campaign={c} onDelete={onDelete} />
      ))}
    </div>
  );
}
```

---

## 23. Run the Frontend

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 — it should redirect to `/dashboard`.

---

## 24. Agent Checklist

Work through these in order:

- [ ] Run `npm install swr zustand framer-motion`
- [ ] Run `npx shadcn@latest add card badge progress table toast separator`
- [ ] Create `frontend/.env.local` with correct values
- [ ] Add CSS variables to `app/globals.css`
- [ ] Create all folders: `components/layout/`, `components/dashboard/`, `components/upload/`, `components/clips/`, `components/campaigns/`, `stores/`
- [ ] Create and fill all files in order: Section 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22
- [ ] Run `npm run dev` and verify http://localhost:3000 loads
- [ ] Verify dashboard shows stats bar and empty job list
- [ ] Verify campaigns page loads and shows existing test campaign
- [ ] Verify upload page shows the form with YouTube URL and file upload tabs
