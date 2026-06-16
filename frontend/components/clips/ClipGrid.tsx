import { Clip } from '@/lib/api';
import ClipCard from './ClipCard';

export default function ClipGrid({ clips }: { clips: Clip[] }) {
  if (clips.length === 0) {
    return <p style={{ color: 'var(--muted)' }}>No clips found for this job.</p>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {clips.map((clip) => (
        <ClipCard key={clip.id} clip={clip} />
      ))}
    </div>
  );
}
