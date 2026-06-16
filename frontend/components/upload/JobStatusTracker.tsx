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
  }, [jobId, onDone]);

  if (!job) return <p style={{ color: 'var(--muted)' }}>Starting job...</p>;

  const currentStep = STEPS.indexOf(job.status);

  return (
    <div
      className="rounded-lg border p-6 space-y-5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div>
        <h2 className="text-lg font-semibold">Processing Job</h2>
        <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Job ID: {jobId}</p>
      </div>

      <div className="space-y-3">
        {STEPS.filter((s) => s !== 'done').map((step, idx) => {
          const done = currentStep > idx;
          const active = currentStep === idx;
          return (
            <div key={step} className="flex items-center gap-3">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: done ? 'var(--accent)' : active ? '#f59e0b' : 'var(--border)',
                }}
              />
              <span
                className="text-sm capitalize"
                style={{ color: done ? 'var(--accent)' : active ? '#f59e0b' : 'var(--muted)' }}
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
