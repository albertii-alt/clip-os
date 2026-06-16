'use client';

import { useEffect, useState } from 'react';
import { use } from 'react';
import { getClips, Clip } from '@/lib/api';
import ClipGrid from '@/components/clips/ClipGrid';

export default function ClipsPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getClips(jobId)
      .then(setClips)
      .finally(() => setLoading(false));
  }, [jobId]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Clips</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>Job ID: {jobId}</p>
      </div>

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading clips...</p>
      ) : (
        <ClipGrid clips={clips} />
      )}
    </div>
  );
}
