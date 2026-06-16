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
        <p className="text-xs" style={{ color: 'var(--muted)' }}>{date}</p>
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
