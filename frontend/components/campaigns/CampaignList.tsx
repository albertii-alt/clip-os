import { Campaign } from '@/lib/api';
import CampaignCard from './CampaignCard';

interface CampaignListProps {
  campaigns: Campaign[];
  onDelete: (id: string) => void;
}

export default function CampaignList({ campaigns, onDelete }: CampaignListProps) {
  if (campaigns.length === 0) {
    return (
      <p style={{ color: 'var(--muted)' }}>
        No campaigns yet. Create one to attach rules to your jobs.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {campaigns.map((c) => (
        <CampaignCard key={c.id} campaign={c} onDelete={onDelete} />
      ))}
    </div>
  );
}
