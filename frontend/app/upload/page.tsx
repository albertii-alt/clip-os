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
