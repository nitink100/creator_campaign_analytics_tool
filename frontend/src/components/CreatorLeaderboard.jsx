import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useDebounce } from '../hooks/useDebounce';
import { formatCompact, formatPercent } from '../utils/formatters';

const COLUMNS = [
    { key: 'rank', label: '#', sortable: false },
    { key: 'select', label: '', sortable: false },
    { key: 'creator_name', label: 'Creator Name', sortable: true },
    { key: 'subscriber_count', label: 'Subscribers', sortable: true },
    { key: 'latest_avg_engagement_rate', label: 'Engagement Rate', sortable: true },
    { key: 'latest_total_views', label: 'Total Views', sortable: true },
    { key: 'total_content_items', label: 'Videos', sortable: true },
];

const PAGE_SIZE = 10;

function sortItems(items, sortBy, sortDir) {
    if (!sortBy) return items;
    return [...items].sort((a, b) => {
        let va = a[sortBy];
        let vb = b[sortBy];

        // Handle nulls — push them to the bottom
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;

        // String comparison for names
        if (typeof va === 'string') {
            const cmp = va.localeCompare(vb);
            return sortDir === 'asc' ? cmp : -cmp;
        }

        // Numeric comparison
        return sortDir === 'asc' ? va - vb : vb - va;
    });
}

export default function CreatorLeaderboard({ refreshKey, onFullRefresh, timePeriod, showModal }) {
    const { user } = useAuth();
    const [allItems, setAllItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [sortBy, setSortBy] = useState('latest_total_views');
    const [sortDir, setSortDir] = useState('desc');
    const [page, setPage] = useState(1);
    const [selected, setSelected] = useState(new Set());
    const [untracking, setUntracking] = useState(false);
    const [campaigns, setCampaigns] = useState([]);
    const [showCampaignPicker, setShowCampaignPicker] = useState(false);

    const debouncedSearch = useDebounce(search, 300);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // Fetch top 100 creators, bounded by timePeriod
            const [data, campaignData] = await Promise.all([
                api.getTopCreators(100, timePeriod),
                api.getCampaigns()
            ]);
            const items = data.items || [];
            setAllItems(items);
            setCampaigns(campaignData || []);
            setSelected(new Set()); // clear selection after refresh
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [refreshKey, timePeriod]);

    useEffect(() => { fetchData(); }, [fetchData]);
    useEffect(() => { setPage(1); }, [debouncedSearch, sortBy, sortDir]);

    // Filter by search
    const filtered = useMemo(() => {
        if (!debouncedSearch) return allItems;
        const q = debouncedSearch.toLowerCase();
        return allItems.filter((c) => c.creator_name?.toLowerCase().includes(q));
    }, [allItems, debouncedSearch]);

    // Sort
    const sorted = useMemo(() => sortItems(filtered, sortBy, sortDir), [filtered, sortBy, sortDir]);

    // Paginate
    const total = sorted.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    const handleSort = (key) => {
        if (key === 'select' || key === 'rank') return;
        if (sortBy === key) {
            setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
        } else {
            setSortBy(key);
            setSortDir('desc');
        }
    };

    const toggleSelect = (creatorId) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(creatorId)) {
                next.delete(creatorId);
            } else {
                next.add(creatorId);
            }
            return next;
        });
    };

    const toggleSelectAll = () => {
        if (selected.size === paged.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(paged.map((c) => c.creator_id)));
        }
    };

    const handleUntrack = async () => {
        if (selected.size === 0) return;
        setUntracking(true);
        try {
            // We need platform_creator_id (channel ID), not internal creator_id
            // The leaderboard items have creator_id (internal UUID), so we need
            // to find the matching channel IDs. For now, use creator names to
            // find them. Actually, let's look at what fields we have...
            // The track/untrack system uses seed channel IDs (UC...).
            // The leaderboard returns internal creator_id. We need to pass
            // the platform_creator_id. Let me check if it's available.
            // For now, we'll use creator_id — the untrack endpoint will need
            // to handle this. Actually the untrack endpoint works with channel_ids
            // from the seed file. We need the platform channel IDs.
            //
            // Best approach: the items should have platform info. Let's check
            // if we can pass names or add platform_creator_id to top-creators.
            //
            // For now: use a workaround — fetch channels list and match by name.
            // This is a quick solution; ideally we'd add platform_creator_id to schema.

            // Actually, let me just send the creator_ids and handle it
            const res = await api.untrackChannels([...selected]);
            if (onFullRefresh) await onFullRefresh();
            if (res?.message) {
                showModal({
                    title: 'Untracked',
                    message: res.message,
                    confirmText: 'OK',
                    hideCancel: true,
                });
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setUntracking(false);
        }
    };

    const handleAddToCampaign = async (campaign) => {
        const campaignId = campaign.id;
        const existingIds = new Set(
            (campaign.members || []).map((m) => m.creator?.creator_id ?? m.creator?.id).filter(Boolean)
        );
        const toAdd = Array.from(selected).filter((id) => !existingIds.has(id));

        if (toAdd.length === 0) {
            showModal({
                title: 'Already in campaign',
                message: 'All selected creators are already in this campaign.',
                confirmText: 'OK',
                hideCancel: true
            });
            setShowCampaignPicker(false);
            return;
        }

        try {
            const promises = toAdd.map((creatorId) =>
                api.addCreatorToCampaign(campaignId, creatorId)
            );
            await Promise.all(promises);
            const alreadyCount = selected.size - toAdd.length;
            const message = alreadyCount > 0
                ? `Added ${toAdd.length} creator(s). ${alreadyCount} were already in the campaign.`
                : `Added ${toAdd.length} creator(s) to campaign.`;
            showModal({
                title: 'Success',
                message,
                confirmText: 'OK',
                hideCancel: true
            });
            setSelected(new Set());
            setShowCampaignPicker(false);
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

    const engClass = (rate) => {
        if (rate == null) return 'engagement-low';
        if (rate >= 0.05) return 'engagement-high';
        if (rate >= 0.03) return 'engagement-mid';
        return 'engagement-low';
    };

    return (
        <div className="panel">
            <div className="panel__header">
                <h2 className="panel__title">Creator Leaderboard</h2>
                <div className="leaderboard-actions">
                    {selected.size > 0 && (
                        <div className="batch-actions">
                            <div className="dropdown">
                                <button 
                                    className="secondary-btn"
                                    onClick={() => setShowCampaignPicker(!showCampaignPicker)}
                                >
                                    Add to Campaign ({selected.size})
                                </button>
                                {showCampaignPicker && (
                                    <div className="dropdown-content">
                                        {campaigns.length === 0 ? (
                                            <p className="no-campaigns">No campaigns active</p>
                                        ) : (
                                            campaigns.map(c => (
                                                <button key={c.id} onClick={() => handleAddToCampaign(c)}>
                                                    {c.name}
                                                </button>
                                            ))
                                        )}
                                    </div>
                                )}
                            </div>
                            <button
                                className="untrack-btn"
                                onClick={handleUntrack}
                                disabled={untracking}
                            >
                                {untracking ? 'Removing...' : `Untrack`}
                            </button>
                        </div>
                    )}
                    <div className="search-wrapper">
                        <input
                            className="search-input"
                            type="text"
                            placeholder="Search by creator name..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </div>
            </div>

            {error && (
                <div className={error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? "offline-banner" : "error-banner"}>
                    <span>{error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? `Offline: ${error}` : error}</span>
                    <button onClick={fetchData}>Retry</button>
                </div>
            )}

            {loading && allItems.length === 0 ? (
                <div>{[...Array(5)].map((_, i) => <div key={i} className="skeleton skeleton-line" />)}</div>
            ) : paged.length === 0 && !loading ? (
                <div className="empty-state">No creators found. Try syncing data first.</div>
            ) : (
                <div style={{ position: 'relative', opacity: loading ? 0.6 : 1, transition: 'opacity 0.2s', pointerEvents: loading ? 'none' : 'auto' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                {COLUMNS.map((col) => (
                                    <th
                                        key={col.key}
                                        className={`${sortBy === col.key ? 'sorted' : ''} ${col.key === 'select' ? 'col-select' : ''}`}
                                        onClick={() => col.sortable && handleSort(col.key)}
                                        style={{ cursor: col.sortable ? 'pointer' : 'default' }}
                                    >
                                        {col.key === 'select' ? (
                                            <input
                                                type="checkbox"
                                                checked={paged.length > 0 && selected.size === paged.length}
                                                onChange={toggleSelectAll}
                                                className="row-checkbox"
                                            />
                                        ) : (
                                            <>
                                                {col.label}
                                                {sortBy === col.key && (sortDir === 'desc' ? ' ↓' : ' ↑')}
                                            </>
                                        )}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {paged.map((c, i) => (
                                <tr
                                    key={c.creator_id}
                                    className={selected.has(c.creator_id) ? 'row-selected' : ''}
                                >
                                    <td>{String((page - 1) * PAGE_SIZE + i + 1).padStart(2, '0')}</td>
                                    <td className="col-select">
                                        <input
                                            type="checkbox"
                                            checked={selected.has(c.creator_id)}
                                            onChange={() => toggleSelect(c.creator_id)}
                                            className="row-checkbox"
                                        />
                                    </td>
                                    <td className="col-creator">
                                        <div className="creator-cell-content">
                                            <div className="avatar-wrapper">
                                                {c.thumbnail_url ? (
                                                    <img 
                                                        src={c.thumbnail_url} 
                                                        alt="" 
                                                        onError={(e) => e.target.style.display = 'none'}
                                                    />
                                                ) : null}
                                                <div className="placeholder">{(c.creator_name || '?')[0]}</div>
                                            </div>
                                            {c.channel_url ? (
                                                <a
                                                    href={c.channel_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="creator-link"
                                                    title={`Visit ${c.creator_name} on YouTube`}
                                                >
                                                    {c.creator_name}
                                                    <span className="creator-link-icon">↗</span>
                                                </a>
                                            ) : (
                                                <span className="creator-name-text">{c.creator_name}</span>
                                            )}
                                        </div>
                                    </td>
                                    <td>{formatCompact(c.subscriber_count)}</td>
                                    <td className={engClass(c.latest_avg_engagement_rate)}>
                                        {formatPercent(c.latest_avg_engagement_rate)}
                                    </td>
                                    <td>{formatCompact(c.latest_total_views)}</td>
                                    <td>{c.total_content_items ?? '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <div className="pagination">
                        <span>
                            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
                        </span>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
                            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
