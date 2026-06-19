'use client';

import { useState } from 'react';
import { Campaign, patchCampaign } from '@/lib/api';

interface CampaignFormProps {
  onSubmit: (data: Omit<Campaign, 'id' | 'created_at'>) => void;
  initial?: Partial<Campaign>;
  campaign?: Campaign;
  onUpdated?: () => void;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs" style={{ color: 'var(--muted)' }}>{label}</label>
      {children}
    </div>
  );
}

export default function CampaignForm({ onSubmit, initial, campaign, onUpdated }: CampaignFormProps) {
  const isEditing = !!campaign;
  const seed = campaign ?? initial;
  const [name, setName] = useState(seed?.name || '');
  const [handle, setHandle] = useState(seed?.creator_handle || '');
  const [platform, setPlatform] = useState(seed?.platform || 'tiktok');
  const [payout, setPayout] = useState(seed?.payout_per_1k || 5);
  const [minLen, setMinLen] = useState(seed?.min_clip_length || 30);
  const [maxLen, setMaxLen] = useState(seed?.max_clip_length || 60);
  const [hashtags, setHashtags] = useState(seed?.required_hashtags?.join(', ') || '');
  const [tags, setTags] = useState(seed?.required_tags?.join(', ') || '');
  const [forbidden, setForbidden] = useState(seed?.forbidden_topics?.join(', ') || '');
  const [styleNotes, setStyleNotes] = useState(seed?.style_notes || '');
  const [layoutStyle, setLayoutStyle] = useState<'full_bleed' | 'boxed'>(seed?.layout_style || 'full_bleed');
  const [bgColor, setBgColor] = useState<'black' | 'white'>(seed?.boxed_background_color || 'black');

  async function handleSubmit() {
    const data = {
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
      layout_style: layoutStyle,
      boxed_background_color: bgColor,
    };
    if (isEditing && campaign) {
      await patchCampaign(campaign.id, data);
      onUpdated?.();
    } else {
      onSubmit(data);
    }
  }

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid var(--border)',
    color: 'var(--text)',
  };

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

      <Field label="Clip Layout">
        <div className="flex gap-2">
          {(['full_bleed', 'boxed'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setLayoutStyle(mode)}
              className="px-3 py-2 rounded text-xs font-medium transition-colors"
              style={{
                background: layoutStyle === mode ? 'var(--accent)' : 'transparent',
                color: layoutStyle === mode ? '#000' : 'var(--muted)',
                border: `1px solid ${layoutStyle === mode ? 'var(--accent)' : 'var(--border)'}`,
              }}
            >
              {mode === 'full_bleed' ? 'Full-bleed crop' : 'Boxed (square + captions outside)'}
            </button>
          ))}
        </div>
      </Field>

      {layoutStyle === 'boxed' && (
        <Field label="Background Color">
          <div className="flex gap-2">
            {(['black', 'white'] as const).map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setBgColor(color)}
                className="px-3 py-2 rounded text-xs font-medium transition-colors capitalize"
                style={{
                  background: bgColor === color ? 'var(--accent)' : 'transparent',
                  color: bgColor === color ? '#000' : 'var(--muted)',
                  border: `1px solid ${bgColor === color ? 'var(--accent)' : 'var(--border)'}`,
                }}
              >
                {color}
              </button>
            ))}
          </div>
        </Field>
      )}
      <button onClick={handleSubmit}
        className="w-full py-2 rounded text-sm font-medium"
        style={{ background: 'var(--accent)', color: '#000' }}>
        {isEditing ? 'Update Campaign' : 'Save Campaign'}
      </button>
    </div>
  );
}
