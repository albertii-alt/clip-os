import { Job } from '@/lib/api';
import JobCard from './JobCard';

interface JobListProps {
  jobs: Job[];
  onRefresh: () => void;
}

export default function JobList({ jobs, onRefresh }: JobListProps) {
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
        <JobCard key={job.id} job={job} onRefresh={onRefresh} />
      ))}
    </div>
  );
}
