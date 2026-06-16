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
