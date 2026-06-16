interface StatsBarProps {
  totalJobs: number;
  totalClips: number;
  totalViews: number;
  totalEarnings: number;
}

export default function StatsBar({ totalJobs, totalClips, totalViews, totalEarnings }: StatsBarProps) {
  const stats = [
    { label: 'Total Jobs', value: totalJobs },
    { label: 'Clips Generated', value: totalClips },
    { label: 'Total Views', value: totalViews.toLocaleString() },
    { label: 'Earnings', value: `$${totalEarnings.toFixed(2)}` },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(({ label, value }) => (
        <div
          key={label}
          className="rounded-lg p-4 border"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
        >
          <p className="text-xs" style={{ color: 'var(--muted)' }}>{label}</p>
          <p className="text-2xl font-bold mt-1" style={{ color: 'var(--accent)' }}>{value}</p>
        </div>
      ))}
    </div>
  );
}
