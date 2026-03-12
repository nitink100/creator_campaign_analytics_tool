import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { formatCompact, formatPercent } from '../utils/formatters';

export default function Campaigns({ showModal }) {
    const [campaigns, setCampaigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [currentCampaign, setCurrentCampaign] = useState(null);
    const [newCampaign, setNewCampaign] = useState({ name: '', description: '', budget: 0, status: 'active' });
    const [showAddMemberModal, setShowAddMemberModal] = useState(false);
    const [availableCreators, setAvailableCreators] = useState([]);
    const [pickerLoading, setPickerLoading] = useState(false);
    const [pickerSearch, setPickerSearch] = useState('');

    const loadCampaigns = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.getCampaigns();
            setCampaigns(res || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadCampaigns();
    }, [loadCampaigns]);

    const handleCreate = async (e) => {
        if (e) e.preventDefault();
        
        if (newCampaign.budget < 0) {
            showModal({
                title: 'Invalid Budget',
                message: 'Budget cannot be negative.',
                confirmText: 'OK',
                hideCancel: true,
                danger: true
            });
            return;
        }

        setSubmitting(true);
        try {
            await api.createCampaign(newCampaign);
            setShowCreateModal(false);
            setNewCampaign({ name: '', description: '', budget: 0, status: 'active' });
            loadCampaigns();
        } catch (err) {
            showModal({
                title: 'Error',
                message: err.message,
                confirmText: 'OK',
                hideCancel: true,
                danger: true
            });
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (id) => {
        showModal({
            title: 'Delete Campaign',
            message: 'Are you sure you want to delete this campaign? This action cannot be undone.',
            confirmText: 'Delete',
            danger: true,
            onConfirm: async () => {
                try {
                    await api.deleteCampaign(id);
                    if (currentCampaign?.id === id) setCurrentCampaign(null);
                    loadCampaigns();
                } catch (err) {
                    showModal({
                        title: 'Error',
                        message: err.message,
                        confirmText: 'OK',
                        hideCancel: true,
                        danger: true
                    });
                }
            }
        });
    };

    const handleViewDetail = async (id) => {
        try {
            const res = await api.getCampaign(id);
            setCurrentCampaign(res);
        } catch (err) {
            showModal({
                title: 'Error',
                message: err.message,
                confirmText: 'OK',
                hideCancel: true,
                danger: true
            });
        }
    };

    const openAddMember = async () => {
        setShowAddMemberModal(true);
        setPickerLoading(true);
        setPickerSearch('');
        try {
            const res = await api.getTopCreators(100);
            const items = res.items || [];
            const existingIds = new Set((currentCampaign.members || []).map(m => m.creator.creator_id));
            setAvailableCreators(items.filter(c => !existingIds.has(c.creator_id)));
        } catch (err) {
            console.error(err);
        } finally {
            setPickerLoading(false);
        }
    };

    const handleRemoveMember = (creatorId) => {
        showModal({
            title: 'Remove Member',
            message: 'Are you sure you want to remove this creator from the campaign?',
            confirmText: 'Remove',
            danger: true,
            onConfirm: async () => {
                try {
                    await api.removeCreatorFromCampaign(currentCampaign.id, creatorId);
                    const updated = await api.getCampaign(currentCampaign.id);
                    setCurrentCampaign(updated);
                } catch (err) {
                    showModal({
                        title: 'Error',
                        message: err.message,
                        confirmText: 'OK',
                        hideCancel: true,
                        danger: true
                    });
                }
            }
        });
    };

    const handleAddMember = async (creatorId) => {
        try {
            await api.addCreatorToCampaign(currentCampaign.id, creatorId);
            const updated = await api.getCampaign(currentCampaign.id);
            setCurrentCampaign(updated);
            setAvailableCreators(prev => prev.filter(c => c.creator_id !== creatorId));
        } catch (err) {
            showModal({
                title: 'Error',
                message: err.message,
                confirmText: 'OK',
                hideCancel: true,
                danger: true
            });
        }
    };

    const filteredPickers = availableCreators.filter(c => 
        c.creator_name.toLowerCase().includes(pickerSearch.toLowerCase())
    );

    return (
        <div className="campaign-container-root">
            {currentCampaign ? (
                <div className="campaign-detail">
                    {showAddMemberModal && (
                        <div className="modal-overlay">
                            <div className="modal picker-modal">
                                <h3>Add Campaign Member</h3>
                                <div className="field">
                                    <label>Search Tracked Creators</label>
                                    <input 
                                        type="text" 
                                        placeholder="e.g. MrBeast, Zach King..." 
                                        value={pickerSearch}
                                        onChange={(e) => setPickerSearch(e.target.value)}
                                        autoFocus
                                    />
                                </div>
                                <div className="picker-list">
                                    {pickerLoading ? (
                                        <div className="state-container sm">
                                            <div className="spinner sm"></div>
                                            <p>Fetching creators...</p>
                                        </div>
                                    ) : filteredPickers.length === 0 ? (
                                        <div className="empty-picker">
                                            <p>{pickerSearch ? 'No matching creators found' : 'No creators tracked yet'}</p>
                                        </div>
                                    ) : (
                                        filteredPickers.map(creator => (
                                            <div key={creator.creator_id} className="picker-creator-item">
                                                <div className="picker-creator-card">
                                                    <div className="picker-avatar">
                                                        {creator.thumbnail_url ? (
                                                            <img 
                                                                src={creator.thumbnail_url} 
                                                                alt="" 
                                                                onError={(e) => e.target.style.display = 'none'}
                                                            />
                                                        ) : null}
                                                        <div className="placeholder">{(creator.creator_name || '?')[0]}</div>
                                                    </div>
                                                    <div className="picker-info">
                                                        <span className="creator-name">{creator.creator_name}</span>
                                                        <div className="creator-stats-chips">
                                                            <div className="stat-chip">
                                                                <span className="chip-label">Subs</span>
                                                                <span className="chip-val">{formatCompact(creator.subscriber_count)}</span>
                                                            </div>
                                                            <div className="stat-chip">
                                                                <span className="chip-label">Videos</span>
                                                                <span className="chip-val">{creator.total_content_items || 0}</span>
                                                            </div>
                                                            <div className="stat-chip engagement">
                                                                <span className="chip-label">Eng. Rate</span>
                                                                <span className="chip-val">{formatPercent(creator.latest_avg_engagement_rate)}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                                <button className="add-btn-premium" onClick={() => handleAddMember(creator.creator_id)}>
                                                    <span>Add</span>
                                                </button>
                                            </div>
                                        ))
                                    )}
                                </div>
                                <div className="actions">
                                    <button className="sync-btn reset-btn" onClick={() => setShowAddMemberModal(false)}>Close</button>
                                </div>
                            </div>
                        </div>
                    )}

                    <header className="section-header">
                        <div className="header-left">
                            <button className="back-btn" onClick={() => setCurrentCampaign(null)}>← Back</button>
                            <h2 className="detail-title">{currentCampaign.name}</h2>
                        </div>
                        <span className={`status-pill ${currentCampaign.status}`}>{currentCampaign.status}</span>
                    </header>

                    <div className="detail-content">
                        <div className="detail-card main-info">
                            <div className="info-group">
                                <label>Description</label>
                                <p className="description">{currentCampaign.description || 'No description provided.'}</p>
                            </div>
                            <div className="detail-stats">
                                <div className="stat-box">
                                    <label>Budget</label>
                                    <div className="value">${currentCampaign.budget.toLocaleString()}</div>
                                </div>
                                <div className="stat-box">
                                    <label>Created (MM/DD/YYYY)</label>
                                    <div className="value">{new Date(currentCampaign.created_at).toLocaleDateString()}</div>
                                </div>
                            </div>
                        </div>

                        <section className="members-section">
                            <div className="section-title-row">
                                <h3>Campaign Members ({currentCampaign.members?.length || 0})</h3>
                                <button className="primary-btn sm" onClick={openAddMember}>+ Add Member</button>
                            </div>
                            {currentCampaign.members?.length > 0 ? (
                                <div className="members-grid">
                                    {currentCampaign.members.map((creator, index) => (
                                        <div className="member-card" key={creator.creator_id || creator.id || index}>
                                            <div className="member-avatar">
                                                {creator.creator?.thumbnail_url ? (
                                                    <img 
                                                        src={creator.creator.thumbnail_url} 
                                                        alt="" 
                                                        onError={(e) => e.target.style.display = 'none'}
                                                    />
                                                ) : null}
                                                <div className="placeholder">{(creator.creator?.creator_name || '?')[0]}</div>
                                            </div>
                                            <div className="member-info">
                                                <div className="member-header">
                                                    <span className="member-name">{creator.creator?.creator_name}</span>
                                                    <button
                                                        className="remove-member-btn"
                                                        onClick={() => handleRemoveMember(creator.creator.creator_id)}
                                                        title="Remove from campaign"
                                                    >
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                                    </button>
                                                </div>
                                                <div className="member-metrics">
                                                    <div className="metric-group">
                                                        <span className="metric-val">{formatCompact(creator.creator?.subscriber_count)}</span>
                                                        <span className="metric-label">subs</span>
                                                    </div>
                                                    <span className="dot">•</span>
                                                    <div className="metric-group">
                                                        <span className="metric-val">{creator.creator?.latest_avg_engagement_rate ? formatPercent(creator.creator.latest_avg_engagement_rate) : '0%'}</span>
                                                        <span className="metric-label">Engagement</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="empty-members">
                                    <p>No creators added to this campaign yet.</p>
                                    <button className="primary-btn sm" onClick={openAddMember}>Add Your First Member</button>
                                </div>
                            )}
                        </section>
                    </div>
                </div>
            ) : (
                <div className="campaign-management-view">
                    <header className="campaign-view-header">
                        <div className="header-content">
                            <div className="title-stack">
                                <h2>Campaign Management</h2>
                            </div>
                        </div>
                        <button className="primary-btn" onClick={() => setShowCreateModal(true)}>
                            <span className="plus">+</span> Create Campaign
                        </button>
                    </header>

                    <div className="campaign-content-wrapper">

                    {showCreateModal && (
                        <div className="modal-overlay">
                            <div className="modal">
                                <h3>Create New Campaign</h3>
                                <div className="field">
                                    <label>Campaign Name</label>
                                    <input
                                        placeholder="e.g., Summer Brand Launch"
                                        value={newCampaign.name}
                                        onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                                        autoFocus
                                    />
                                </div>
                                <div className="field">
                                    <label>Description</label>
                                    <textarea
                                        placeholder="Describe the campaign objectives..."
                                        rows={4}
                                        value={newCampaign.description}
                                        onChange={(e) => setNewCampaign({ ...newCampaign, description: e.target.value })}
                                    />
                                </div>
                                <div className="field">
                                    <label>Budget ($)</label>
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        placeholder="0"
                                        value={newCampaign.budget === 0 ? '' : String(newCampaign.budget)}
                                        onChange={(e) => {
                                            const v = e.target.value.replace(/\D/g, '');
                                            setNewCampaign({ ...newCampaign, budget: v === '' ? 0 : Math.max(0, parseInt(v, 10)) });
                                        }}
                                    />
                                </div>
                                <div className="actions">
                                    <button 
                                        className="sync-btn reset-btn" 
                                        style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                                        onClick={() => setShowCreateModal(false)}
                                        disabled={submitting}
                                    >
                                        Cancel
                                    </button>
                                    <button 
                                        className="sync-btn" 
                                        onClick={handleCreate}
                                        disabled={submitting || !newCampaign.name.trim()}
                                    >
                                        {submitting ? 'Creating...' : 'Create Campaign'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {loading ? (
                        <div className="state-container">
                            <div className="spinner"></div>
                            <p>Loading campaigns...</p>
                        </div>
                    ) : error ? (
                        <div className="state-container error-state">
                            <h3>Oops! Something went wrong</h3>
                            <p className="error-msg">{error}</p>
                            <button className="secondary-btn" style={{marginTop: "16px"}} onClick={loadCampaigns}>
                                Try Again
                            </button>
                        </div>
                    ) : campaigns.length === 0 ? (
                        <div className="state-container empty-state">
                            <div className="empty-icon">📁</div>
                            <h3>No campaigns yet</h3>
                            <p>Create your first campaign to add creators and see how they perform.</p>
                        </div>
                    ) : (
                        <div className="campaigns-grid">
                            {campaigns.map(c => (
                                <div key={c.id} className="campaign-card">
                                    <div className="card-header">
                                        <h4 className="card-title-premium">{c.name}</h4>
                                        <span className={`status-pill ${c.status}`}>{c.status}</span>
                                    </div>
                                    <div className="card-description-bifurcation">
                                        <div className="separator-line"></div>
                                        <label className="tiny-label">Campaign Description</label>
                                        <p className="description-preview">{c.description || 'No description provided.'}</p>
                                    </div>
                                    <div className="card-footer">
                                        <span>${c.budget.toLocaleString()}</span>
                                        <div className="actions">
                                            <button className="view-btn" onClick={() => handleViewDetail(c.id)}>View</button>
                                            <button className="delete-btn" onClick={() => handleDelete(c.id)}>Delete</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        )}
    </div>
    );
}
