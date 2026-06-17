'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Job, cancelJob, deleteJob, retryJob } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  queued: '#666666',
  downloading: '#f59e0b',
  transcribing: '#3b82f6',
  analyzing: '#8b5cf6',
  rendering: '#f97316',
  done: '#4ADE80',
  failed: '#ef4444',
  cancelled: '#666666',
};

const CANCELLABLE = new Set(['queued', 'downloading', 'transcribing', 'analyzing', 'rendering']);

interface JobCardProps {
  job: Job;
  onRefresh: () => void;
}

export default function JobCard({ job, onRefresh }: JobCardProps) {
  const color = STATUS_COLORS[job.status] || '#666666';
  const date = new Date(job.created_at).toLocaleDateString();
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState('');

  async function handleCancel() {
    try {
      await cancelJob(job.id);
      onRefresh();
    } catch {}
  }

  async function handleDelete() {
    if (!window.confirm('Delete this job and all its clips permanently?')) return;
    try {
      await deleteJob(job.id);
      onRefresh();
    } catch {}
  }

  async function handleRetry() {
    setRetryError('');
    setRetrying(true);
    try {
      await retryJob(job.id);
      onRefresh();
    } catch (e: unknown) {
      setRetryError(e instanceof Error ? e.message : 'Failed to retry job');
    } finally {
      setRetrying(false);
    }
  }

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
        {retryError && (
          <p className="text-xs" style={{ color: '#ef4444' }}>{retryError}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <span
          className="text-xs font-medium px-2 py-1 rounded-full"
          style={{ background: `${color}20`, color }}
        >
          {job.status}
        </span>

        {job.status === 'done' && (
          <Link
            href={`/clips/${job.id}`}
            className="text-xs px-3 py-1 rounded-md font-medium"
            style={{ background: 'var(--accent)', color: '#000' }}
          >
            View Clips
          </Link>
        )}

        {job.status === 'failed' && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="text-xs px-3 py-1 rounded-md font-medium transition-opacity"
            style={{ background: 'var(--accent)', color: '#000', opacity: retrying ? 0.6 : 1 }}
          >
            {retrying ? 'Retrying...' : 'Retry'}
          </button>
        )}

        {CANCELLABLE.has(job.status) && (
          <button
            onClick={handleCancel}
            className="text-xs px-3 py-1 rounded-md font-medium"
            style={{ background: '#ef444420', color: '#ef4444' }}
          >
            Cancel
          </button>
        )}

        <button
          onClick={handleDelete}
          className="text-xs px-3 py-1 rounded-md font-medium"
          style={{ background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)' }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
