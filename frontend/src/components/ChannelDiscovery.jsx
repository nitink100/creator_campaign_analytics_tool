import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { formatCompact } from '../utils/formatters';

/* ── helpers ─────────────────────────────────────────────── */

function looksLikeHandleOrUrl(input) {
    const q = input.trim();
    if (!q || q === '@') return false;
    if (q.startsWith('@')) return true;
    if (q.startsWith('UC') && q.length === 24) return true;
    if (q.includes('youtube.com') || q.includes('youtu.be')) return true;
    return false;
}

/* ── sub-components ──────────────────────────────────────── */

function QuotaBar({ quota }) {
    if (!quota || quota.limit === undefined) return null;
    const pct = quota.percent || 0;
    const barClass = pct >= 90 ? 'quota-critical' : pct >= 65 ? 'quota-warn' : 'quota-ok';
    return (
        <div className={`quota-bar ${barClass}`}>
            <div className="quota-bar__fill" style={{ width: `${Math.min(pct, 100)}%` }} />
            <span className="quota-bar__label">
                ⚡ API Quota: {quota.used?.toLocaleString()} / {quota.limit?.toLocaleString()} ({pct}%)
                {pct >= 65 && ' ⚠️ Approaching limit'}
                {pct >= 90 && ' — Search disabled'}
            </span>
        </div>
    );
}

function ChannelCard({ channel, onTrack, tracking }) {
    const initial = (channel.name || '?').charAt(0).toUpperCase();
    return (
        <div className="channel-card">
            <div className="channel-card__avatar">
                {channel.thumbnail_url ? (
                    <img
                        src={channel.thumbnail_url}
                        alt=""
                        onError={(e) => { e.target.style.display = 'none'; e.target.nextElementSibling?.classList.add('visible'); }}
                    />
                ) : null}
                <span className="channel-card__initial">{initial}</span>
            </div>
            <div className="channel-card__info">
                <div className="channel-card__name">{channel.name}</div>
                <div className="channel-card__meta">
                    {channel.handle && <span>{channel.handle}</span>}
                    {channel.subscribers != null && (
                        <span>{formatCompact(channel.subscribers)} subscribers</span>
                    )}
                </div>
                {channel.description && (
                    <div className="channel-card__desc">{channel.description}</div>
                )}
            </div>
            {channel.already_tracked ? (
                <span className="channel-card__badge tracked">✓ Tracked</span>
            ) : (
                <button
                    className="channel-card__badge track-btn"
                    onClick={() => onTrack(channel.channel_id)}
                    disabled={tracking === channel.channel_id}
                >
                    {tracking === channel.channel_id ? '⟳...' : '+ Track'}
                </button>
            )}
        </div>
    );
}

/* ── main component ──────────────────────────────────────── */

export default function ChannelDiscovery({ refreshKey, onChannelTracked }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [categories, setCategories] = useState([]);
    const [activeCategory, setActiveCategory] = useState(null);
    const [trendingResults, setTrendingResults] = useState([]);
    const [trackedIds, setTrackedIds] = useState([]);
    const [quota, setQuota] = useState({});
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [tracking, setTracking] = useState(null);
    const [trendingSort, setTrendingSort] = useState('subscribers');
    const debounceRef = useRef(null);

    // Load categories + tracked channels on mount
    useEffect(() => {
        (async () => {
            try {
                const [catRes, chRes, qRes] = await Promise.all([
                    api.getCategories(),
                    api.getChannels(),
                    api.getQuota(),
                ]);
                setCategories(catRes.categories || []);
                const currentTrackedIds = chRes.channel_ids || [];
                setTrackedIds(currentTrackedIds);
                setQuota(qRes);

                // Update local search/trending results tracking states
                setResults(prev => prev.map(ch => ({
                    ...ch,
                    already_tracked: currentTrackedIds.includes(ch.channel_id)
                })));
                setTrendingResults(prev => prev.map(ch => ({
                    ...ch,
                    already_tracked: currentTrackedIds.includes(ch.channel_id)
                })));

            } catch (err) {
                console.error('Failed to load discovery data:', err);
            }
        })();
    }, [refreshKey]);

    // Debounced search
    const handleInputChange = useCallback((e) => {
        const val = e.target.value;
        setQuery(val);
        setError('');
        setMessage('');

        if (debounceRef.current) clearTimeout(debounceRef.current);

        if (!val.trim() || val.trim() === '@') {
            setResults([]);
            return;
        }

        debounceRef.current = setTimeout(async () => {
            setLoading(true);
            try {
                if (looksLikeHandleOrUrl(val)) {
                    const res = await api.resolveChannel(val.trim());
                    setQuota(res.quota || {});
                    
                    // The backend now returns success flag to avoid 500s
                    if (res.success !== false && res.channel) {
                        setResults([res.channel]);
                        setMessage(res.message);
                    } else {
                        setResults([]);
                        setMessage(res.message || 'No channel found');
                    }
                } else {
                    const res = await api.searchChannels(val.trim(), 5);
                    setQuota(res.quota || {});
                    
                    if (res.success !== false && res.results?.length) {
                        setResults(res.results);
                        setMessage(res.message);
                    } else {
                        setResults([]);
                        setMessage(res.message || 'No results');
                    }
                }
            } catch (err) {
                setError(err.message || 'Search failed. Please try a different query.');
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, 500);
    }, []);

    // Category click
    const handleCategoryClick = useCallback(async (catId) => {
        if (activeCategory === catId) {
            setActiveCategory(null);
            setTrendingResults([]);
            return;
        }
        setActiveCategory(catId);
        setLoading(true);
        setError('');
        try {
            const res = await api.getTrending(catId);
            setQuota(res.quota || {});
            setTrendingResults(res.creators || []);
            const catName = categories.find((c) => c.id === catId)?.title || catId;
            setMessage(res.creators?.length
                ? `${res.creators.length} trending creator(s) in ${catName}`
                : `No trending creators found in ${catName}`);
        } catch (err) {
            const catName = categories.find((c) => c.id === catId)?.title || catId;
            setMessage(`No trending creators available for ${catName}`);
            setTrendingResults([]);
        } finally {
            setLoading(false);
        }
    }, [activeCategory, categories]);

    // Track channel
    const handleTrack = useCallback(async (channelId) => {
        setTracking(channelId);
        setError('');
        try {
            const res = await api.trackChannel(channelId);
            setQuota(res.quota || {});
            setMessage(res.message || 'Channel tracked!');

            // Update tracked status in results
            setResults((prev) =>
                prev.map((ch) =>
                    ch.channel_id === channelId ? { ...ch, already_tracked: true } : ch
                )
            );
            setTrendingResults((prev) =>
                prev.map((ch) =>
                    ch.channel_id === channelId ? { ...ch, already_tracked: true } : ch
                )
            );
            setTrackedIds((prev) =>
                prev.includes(channelId) ? prev : [...prev, channelId]
            );

            if (onChannelTracked) onChannelTracked();
        } catch (err) {
            setError(err.message);
        } finally {
            setTracking(null);
        }
    }, [onChannelTracked]);

    const showResults = results.length > 0;
    const showTrending = trendingResults.length > 0 && !showResults;

    return (
        <div className="panel discovery-panel">
            <div className="panel__header">
                <h2 className="panel__title">🔍 Discover Channels</h2>
            </div>

            {/* Search bar */}
            <div className="discovery-search">
                <input
                    className="discovery-search__input"
                    type="text"
                    placeholder="Search by name, @handle, or paste YouTube Channel URL..."
                    value={query}
                    onChange={handleInputChange}
                />
                {loading && <span className="discovery-search__spinner">⟳</span>}
            </div>

            {/* Messages */}
            {error && <div className="discovery-msg error">{error}</div>}
            {message && !error && <div className="discovery-msg info">{message}</div>}

            {/* Search results */}
            {showResults && (
                <div className="discovery-results">
                    {results.map((ch) => (
                        <ChannelCard
                            key={ch.channel_id}
                            channel={ch}
                            onTrack={handleTrack}
                            tracking={tracking}
                        />
                    ))}
                </div>
            )}

            {/* Category bar */}
            {!showResults && (
                <>
                    <div className="discovery-divider">Browse by Category</div>
                    <div className="category-bar">
                        {categories.map((cat) => (
                            <button
                                key={cat.id}
                                className={`category-pill ${activeCategory === cat.id ? 'active' : ''}`}
                                onClick={() => handleCategoryClick(cat.id)}
                            >
                                {cat.title}
                            </button>
                        ))}
                    </div>
                </>
            )}

            {/* Trending results */}
            {showTrending && (
                <>
                    <div className="discovery-sort-bar">
                        <span>Sort by:</span>
                        <select
                            value={trendingSort}
                            onChange={(e) => setTrendingSort(e.target.value)}
                            className="discovery-sort-select"
                        >
                            <option value="subscribers">Subscribers (High → Low)</option>
                            <option value="name">Name (A → Z)</option>
                        </select>
                    </div>
                    <div className="discovery-results">
                        {[...trendingResults]
                            .sort((a, b) => {
                                if (trendingSort === 'subscribers')
                                    return (b.subscribers || 0) - (a.subscribers || 0);
                                return (a.name || '').localeCompare(b.name || '');
                            })
                            .map((ch) => (
                                <ChannelCard
                                    key={ch.channel_id}
                                    channel={ch}
                                    onTrack={handleTrack}
                                    tracking={tracking}
                                />
                            ))}
                    </div>
                </>
            )}

            {/* Quota indicator */}
            <QuotaBar quota={quota} />
        </div>
    );
}
