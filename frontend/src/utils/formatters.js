export function formatCompact(n) {
    if (n == null) return '—';
    return Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

export function formatPercent(rate) {
    if (rate == null) return '—';
    return `${(rate * 100).toFixed(1)}%`;
}

export function timeAgo(dateStr) {
    if (!dateStr) return '—';
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diff = now - then;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    const weeks = Math.floor(days / 7);
    return `${weeks}w ago`;
}

export function formatNumber(n) {
    if (n == null) return '—';
    return Intl.NumberFormat('en').format(n);
}
