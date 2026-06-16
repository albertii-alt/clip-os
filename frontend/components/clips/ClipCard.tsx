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
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Clip #{clip.clip_index}</span>
        <span
          className="text-xs px-2 py-1 rounded-full font-medium"
          style={{ background: 'rgba(74,222,128,0.1)', color: 'var(--accent)' }}
        >
          Score: {clip.viral_score ?? '—'}
        </span>
      </div>

      {clip.hook && (
        <p className="text-sm italic" style={{ color: 'var(--muted)' }}>
          &quot;{clip.hook}&quot;
        </p>
      )}

      <div className="flex gap-4 text-xs" style={{ color: 'var(--muted)' }}>
        <span>{duration}s</span>
        <span className="capitalize">{clip.category?.replace('_', ' ')}</span>
      </div>

      {clip.score_reason && (
        <p className="text-xs" style={{ color: 'var(--muted)' }}>{clip.score_reason}</p>
      )}

      {clip.public_url && (
        <video
          src={clip.public_url}
          controls
          className="w-full rounded-md"
          style={{ maxHeight: '300px' }}
        />
      )}

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

      <div className="border-t pt-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
        <p className="text-xs font-medium" style={{ color: 'var(--muted)' }}>Track Performance</p>
        <div className="flex gap-2">
          <input
            type="number"
            value={views}
            onChange={(e) => setViews(Number(e.target.value))}
            placeholder="Views"
            className="flex-1 px-2 py-1 rounded text-xs outline-none"
            style={{ background: '#1a1a1a', border: '1px solid var(--border)', color: 'var(--text)' }}
          />
          <input
            type="number"
            value={earnings}
            onChange={(e) => setEarnings(Number(e.target.value))}
            placeholder="Earnings $"
            className="flex-1 px-2 py-1 rounded text-xs outline-none"
            style={{ background: '#1a1a1a', border: '1px solid var(--border)', color: 'var(--text)' }}
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
