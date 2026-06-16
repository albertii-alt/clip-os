'use client';

import { useState, useEffect } from 'react';
import { getCampaigns, createJobFromUrl, createJobFromLocalPath, Campaign } from '@/lib/api';

interface UploadFormProps {
  onJobCreated: (jobId: string) => void;
}

export default function UploadForm({ onJobCreated }: UploadFormProps) {
  const [mode, setMode] = useState<'url' | 'local_path'>('url');
  const [url, setUrl] = useState('');
  const [localPath, setLocalPath] = useState('');
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
        if (!localPath) throw new Error('Please enter a local file path');
        result = await createJobFromLocalPath(localPath, campaignId || undefined);
      }
      onJobCreated(result.job_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid var(--border)',
    color: 'var(--text)',
  };

  return (
    <div
      className="rounded-lg border p-6 space-y-5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="flex gap-2">
        {(['url', 'local_path'] as const).map((m) => (
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
            {m === 'url' ? 'YouTube URL' : 'Local Path'}
          </button>
        ))}
      </div>

      {mode === 'url' ? (
        <div className="space-y-2">
          <label className="text-sm" style={{ color: 'var(--muted)' }}>YouTube URL</label>
          <input
            key="url-input"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full px-3 py-2 rounded-md text-sm outline-none"
            style={inputStyle}
          />
        </div>
      ) : (
        <div className="space-y-2">
          <label className="text-sm" style={{ color: 'var(--muted)' }}>Local File Path</label>
          <input
            key="localpath-input"
            type="text"
            value={localPath}
            onChange={(e) => setLocalPath(e.target.value)}
            placeholder="C:\Videos\myvideo.mp4"
            className="w-full px-3 py-2 rounded-md text-sm outline-none"
            style={inputStyle}
          />
        </div>
      )}

      <div className="space-y-2">
        <label className="text-sm" style={{ color: 'var(--muted)' }}>Campaign (optional)</label>
        <select
          value={campaignId}
          onChange={(e) => setCampaignId(e.target.value)}
          className="w-full px-3 py-2 rounded-md text-sm outline-none"
          style={inputStyle}
        >
          <option value="">No campaign</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} — {c.platform}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-2 rounded-md text-sm font-medium transition-opacity"
        style={{ background: 'var(--accent)', color: '#000', opacity: loading ? 0.6 : 1 }}
      >
        {loading ? 'Submitting...' : 'Generate Clips'}
      </button>
    </div>
  );
}
