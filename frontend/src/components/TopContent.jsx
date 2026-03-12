import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { formatCompact, formatPercent, timeAgo } from '../utils/formatters';

const PAGE_SIZE = 10;
const FETCH_LIMIT = 250;

const COLUMNS = [
    { key: 'title', label: 'Video Title', sortable: true },
    { key: 'creator_name', label: 'Creator', sortable: true },
    { key: 'views', label: 'Views', sortable: true },
    { key: 'likes', label: 'Likes', sortable: true },
    { key: 'comments', label: 'Comments', sortable: true },
    { key: 'engagement_rate', label: 'Engagement', sortable: true },
    { key: 'published_at', label: 'Published', sortable: true },
];

function sortItems(items, sortBy, sortDir) {
    if (!sortBy) return items;
    return [...items].sort((a, b) => {
        let va = a[sortBy];
        let vb = b[sortBy];
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === 'string') {
            const cmp = va.localeCompare(vb);
            return sortDir === 'asc' ? cmp : -cmp;
        }
        return sortDir === 'asc' ? va - vb : vb - va;
    });
}

export default function TopContent({ timePeriod, refreshKey, creators = [] }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sortBy, setSortBy] = useState('views');
    const [sortDir, setSortDir] = useState('desc');
    const [creatorFilter, setCreatorFilter] = useState('');
    const [page, setPage] = useState(1);

    const fetchData = useCallback(async () => {
        setLoading(true);
        setError(null);
        setPage(1);
        try {
            const data = await api.getTopContent(FETCH_LIMIT, timePeriod, creatorFilter || null);
            setItems(data.items || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [timePeriod, refreshKey, creatorFilter]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const creatorNames = useMemo(() => {
        const names = [...new Set(creators.map((c) => c.creator_name).filter(Boolean))];
        return names.sort();
    }, [creators]);

    const sorted = useMemo(() => sortItems(items, sortBy, sortDir), [items, sortBy, sortDir]);
    const total = sorted.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const start = (page - 1) * PAGE_SIZE;
    const pagedItems = useMemo(
        () => sorted.slice(start, start + PAGE_SIZE),
        [sorted, start]
    );

    const handleSort = (key) => {
        setPage(1);
        if (sortBy === key) {
            setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
        } else {
            setSortBy(key);
            setSortDir('desc');
        }
    };

    const engClass = (rate) => {
        if (rate == null) return 'engagement-low';
        if (rate >= 0.05) return 'engagement-high';
        if (rate >= 0.03) return 'engagement-mid';
        return 'engagement-low';
    };

    if (loading && items.length === 0) {
        return (
            <div className="panel">
                <div className="panel__header">
                    <h2 className="panel__title">Top Performing Content</h2>
                    {creatorNames.length > 1 && (
                        <select
                            className="content-creator-filter"
                            value={creatorFilter}
                            onChange={(e) => setCreatorFilter(e.target.value)}
                            disabled
                        >
                            <option value="">All Creators ({creatorNames.length})</option>
                        </select>
                    )}
                </div>
                {[...Array(5)].map((_, i) => <div key={i} className="skeleton skeleton-line" />)}
            </div>
        );
    }

    return (
        <div className="panel">
            <div className="panel__header">
                <h2 className="panel__title">Top Performing Content</h2>
                {creatorNames.length > 1 && (
                    <select
                        className="content-creator-filter"
                        value={creatorFilter}
                        onChange={(e) => setCreatorFilter(e.target.value)}
                        disabled={loading}
                    >
                        <option value="">All Creators ({creatorNames.length})</option>
                        {creatorNames.map((name) => (
                            <option key={name} value={name}>{name}</option>
                        ))}
                    </select>
                )}
            </div>
            {error && (
                <div className={error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? "offline-banner" : "error-banner"}>
                    <span>{error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? `Offline: ${error}` : error}</span>
                    <button onClick={fetchData}>Retry</button>
                </div>
            )}
            
            {!loading && sorted.length === 0 ? (
                <div className="empty-state">No content data matching criteria</div>
            ) : (
                <div style={{ position: 'relative' }}>
                    {loading && (
                        <div style={{ position: 'absolute', inset: 0, background: 'rgba(15, 17, 26, 0.6)', backdropFilter: 'blur(2px)', zIndex: 10, borderRadius: 'var(--radius-md)' }} />
                    )}
                    <table className="data-table">
                        <thead>
                            <tr>
                                {COLUMNS.map((col) => (
                                    <th
                                        key={col.key}
                                        className={sortBy === col.key ? 'sorted' : ''}
                                        onClick={() => col.sortable && handleSort(col.key)}
                                        style={{ cursor: col.sortable ? 'pointer' : 'default' }}
                                    >
                                        {col.label}
                                        {sortBy === col.key && (sortDir === 'desc' ? ' ↓' : ' ↑')}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {pagedItems.map((item) => (
                                <tr key={item.content_id}>
                                    <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {item.content_url ? (
                                            <a
                                                href={item.content_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="content-link"
                                                title={item.title}
                                            >
                                                {item.title}
                                            </a>
                                        ) : (
                                            item.title
                                        )}
                                    </td>
                                    <td>{item.creator_name}</td>
                                    <td>{formatCompact(item.views)}</td>
                                    <td>{formatCompact(item.likes)}</td>
                                    <td>{formatCompact(item.comments)}</td>
                                    <td className={engClass(item.engagement_rate)}>
                                        {formatPercent(item.engagement_rate)}
                                    </td>
                                    <td>{timeAgo(item.published_at)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {total > PAGE_SIZE && (
                        <div className="pagination">
                            <span>
                                Showing {start + 1}–{Math.min(start + PAGE_SIZE, total)} of {total}
                            </span>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button
                                    type="button"
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    disabled={page <= 1}
                                >
                                    Previous
                                </button>
                                <span style={{ alignSelf: 'center', fontSize: 12, color: 'var(--text-secondary)' }}>
                                    Page {page} of {totalPages}
                                </span>
                                <button
                                    type="button"
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    disabled={page >= totalPages}
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
