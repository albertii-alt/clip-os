'use client';

import { useEffect, useState } from 'react';
import { getJobs, getClips, Job, Clip } from '@/lib/api';
import JobList from '@/components/dashboard/JobList';
import StatsBar from '@/components/dashboard/StatsBar';

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [allClips, setAllClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const jobsData = await getJobs();
        setJobs(jobsData);
        const doneJobs = jobsData.filter((j) => j.status === 'done');
        const results = await Promise.allSettled(doneJobs.map((j) => getClips(j.id)));
        const clips = results
          .filter((r): r is PromiseFulfilledResult<Clip[]> => r.status === 'fulfilled')
          .flatMap((r) => r.value);
        setAllClips(clips);
      } catch (e) {
        setError('Could not reach the backend. Is it running?');
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
