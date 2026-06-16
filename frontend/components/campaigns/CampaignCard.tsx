import { Campaign } from '@/lib/api';

interface CampaignCardProps {
  campaign: Campaign;
  onDelete: (id: string) => void;
}

export default function CampaignCard({ campaign, onDelete }: CampaignCardProps) {
  return (
    <div
      className="rounded-lg border p-4 space-y-2"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">{campaign.name}</p>
        <button
          onClick={() => onDelete(campaign.id)}
          className="text-xs px-2 py-1 rounded"
          style={{ background: '#ef444420', color: '#ef4444' }}
        >
          Delete
        </button>
      </div>
      <div className="flex gap-3 text-xs" style={{ color: 'var(--muted)' }}>
        <span className="capitalize">{campaign.platform}</span>
        <span>${campaign.payout_per_1k}/1K views</span>
        <span>{campaign.min_clip_length}s – {campaign.max_clip_length}s</span>
      </div>
      {campaign.required_hashtags.length > 0 && (
        <p className="text-xs" style={{ color: 'var(--accent)' }}>
          {campaign.required_hashtags.join(' ')}
        </p>
      )}
    </div>
  );
}
