import React, { useMemo } from 'react';
import { Scatter } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    LinearScale,
    LogarithmicScale,
    PointElement,
    Tooltip,
} from 'chart.js';

ChartJS.register(LinearScale, LogarithmicScale, PointElement, Tooltip);

function getQuadrant(subs, eng, medianSubs, medianEng) {
    if (eng >= medianEng && subs < medianSubs) return 'gem';
    if (eng >= medianEng && subs >= medianSubs) return 'power';
    if (eng < medianEng && subs >= medianSubs) return 'decline';
    return 'emerging';
}

const COLORS = {
    gem: '#22c55e',
    power: '#3b82f6',
    decline: '#f97316',
    emerging: '#64748b',
};

export default function EngagementChart({ creators, loading }) {
    const chartData = useMemo(() => {
        if (!creators || creators.length === 0) return null;

        const valid = creators.filter(
            (c) => c.subscriber_count != null && c.latest_avg_engagement_rate != null
        );
        if (valid.length === 0) return null;

        const subs = valid.map((c) => c.subscriber_count).sort((a, b) => a - b);
        const engs = valid.map((c) => c.latest_avg_engagement_rate).sort((a, b) => a - b);
        const medianSubs = subs[Math.floor(subs.length / 2)];
        const medianEng = engs[Math.floor(engs.length / 2)];

        const points = valid.map((c) => {
            const q = getQuadrant(c.subscriber_count, c.latest_avg_engagement_rate, medianSubs, medianEng);
            return {
                x: c.subscriber_count,
                y: c.latest_avg_engagement_rate * 100,
                label: c.creator_name,
                color: COLORS[q],
            };
        });

        return {
            datasets: [
                {
                    data: points,
                    backgroundColor: points.map((p) => p.color),
                    pointRadius: 8,
                    pointHoverRadius: 11,
                },
            ],
        };
    }, [creators]);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                type: 'logarithmic',
                title: { display: true, text: 'Subscribers (Log)', color: '#8b8fa3', font: { size: 11 } },
                grid: { color: 'rgba(42,45,62,0.5)' },
                ticks: { color: '#5a5e72', callback: (v) => Intl.NumberFormat('en', { notation: 'compact' }).format(v) },
            },
            y: {
                title: { display: true, text: 'Engagement %', color: '#8b8fa3', font: { size: 11 } },
                grid: { color: 'rgba(42,45,62,0.5)' },
                ticks: { color: '#5a5e72', callback: (v) => `${v.toFixed(1)}%` },
                beginAtZero: true,
            },
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const p = ctx.raw;
                        return `${p.label}: ${Intl.NumberFormat('en', { notation: 'compact' }).format(p.x)} subs, ${p.y.toFixed(1)}% eng`;
                    },
                },
            },
            legend: { display: false },
        },
    };

    return (
        <div className="panel">
            <div className="panel__header">
                <h2 className="panel__title">Engagement vs Reach</h2>
            </div>
            {loading ? (
                <div className="skeleton" style={{ height: 320 }} />
            ) : !chartData ? (
                <div className="empty-state">No engagement data available</div>
            ) : (
                <>
                    <div className="chart-container">
                        <Scatter data={chartData} options={options} />
                    </div>
                    <div className="chart-legend">
                        <span className="legend-gem">Hidden Gems</span>
                        <span className="legend-power">Power Creators</span>
                        <span className="legend-decline">Declining</span>
                        <span className="legend-emerging">Emerging</span>
                    </div>
                </>
            )}
        </div>
    );
}
