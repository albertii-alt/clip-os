'use client';

import { useEffect, useState } from 'react';
import { getCampaigns, createCampaign, deleteCampaign, Campaign } from '@/lib/api';
import CampaignList from '@/components/campaigns/CampaignList';
import CampaignForm from '@/components/campaigns/CampaignForm';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    const data = await getCampaigns();
    setCampaigns(data);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(data: Omit<Campaign, 'id' | 'created_at'>) {
    await createCampaign(data);
    setShowForm(false);
    load();
  }

  async function handleDelete(id: string) {
    await deleteCampaign(id);
    if (editingCampaign?.id === id) setEditingCampaign(null);
    load();
  }

  function handleEdit(campaign: Campaign) {
    setEditingCampaign(campaign);
    setShowForm(false);
  }

  function handleUpdated() {
    setEditingCampaign(null);
    load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Campaigns</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--muted)' }}>
            Manage your Whop clipping campaigns
          </p>
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setEditingCampaign(null); }}
          className="px-4 py-2 rounded-md text-sm font-medium"
          style={{ background: 'var(--accent)', color: '#000' }}
        >
          {showForm ? 'Cancel' : '+ New Campaign'}
        </button>
      </div>

      {showForm && <CampaignForm onSubmit={handleCreate} />}

      {editingCampaign && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium" style={{ color: 'var(--muted)' }}>
              Editing: {editingCampaign.name}
            </p>
            <button
              onClick={() => setEditingCampaign(null)}
              className="text-xs px-2 py-1 rounded"
              style={{ color: 'var(--muted)', border: '1px solid var(--border)' }}
            >
              Cancel Edit
            </button>
          </div>
          <CampaignForm
            onSubmit={handleCreate}
            campaign={editingCampaign}
            onUpdated={handleUpdated}
          />
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading...</p>
      ) : (
        <CampaignList campaigns={campaigns} onDelete={handleDelete} onEdit={handleEdit} />
      )}
    </div>
  );
}
