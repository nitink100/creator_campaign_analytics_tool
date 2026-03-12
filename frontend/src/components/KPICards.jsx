import React from 'react';
import { formatCompact, formatPercent } from '../utils/formatters';

const ICONS = ['👥', '🎬', '📈', '👁️', '👑'];

export default function KPICards({ summary, loading }) {
    if (loading && !summary) {
        return (
            <div className="kpi-row">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="kpi-card"><div className="skeleton skeleton-card" /></div>
                ))}
            </div>
        );
    }

    if (!summary) return null;

    const cards = [
        { label: 'Total Creators', value: summary.total_creators, icon: ICONS[0] },
        { label: 'Total Videos', value: summary.total_content_items, icon: ICONS[1] },
        { label: 'Avg Engagement', value: formatPercent(summary.avg_engagement_rate), icon: ICONS[2], raw: true },
        { label: 'Total Views', value: formatCompact(summary.total_views), icon: ICONS[3], raw: true },
        { label: 'Top Creator', value: summary.top_creator_name || '—', icon: ICONS[4], raw: true },
    ];

    return (
        <div className="kpi-row">
            {cards.map((c) => (
                <div className="kpi-card" key={c.label}>
                    <span className="kpi-card__label">
                        {c.label}
                        <span className="kpi-card__icon">{c.icon}</span>
                    </span>
                    <span className="kpi-card__value">
                        {c.raw ? c.value : formatCompact(c.value)}
                    </span>
                </div>
            ))}
        </div>
    );
}
