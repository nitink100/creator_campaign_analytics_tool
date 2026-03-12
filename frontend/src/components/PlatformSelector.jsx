import React from 'react';

const PLATFORMS = [
    { id: 'youtube', label: 'YouTube', icon: '▶', color: '#ff0000', active: true },
    { id: 'tiktok', label: 'TikTok', icon: '♪', color: '#69c9d0', active: false },
    { id: 'instagram', label: 'Instagram', icon: '📷', color: '#e1306c', active: false },
    { id: 'twitch', label: 'Twitch', icon: '🟣', color: '#9146ff', active: false },
];

export default function PlatformSelector({ selected, onSelect, hideTitle }) {
    return (
        <div className={`platform-selector ${hideTitle ? 'platform-selector--no-title' : ''}`}>
            {!hideTitle && (
                <div className="platform-selector__header">
                    <h1 className="platform-selector__title">Creator Campaign Analytics</h1>
                    <span className="platform-selector__subtitle">Track creator performance and campaign results in one place</span>
                </div>
            )}
            <div className="platform-tabs">
                {PLATFORMS.map((p) => (
                    <button
                        key={p.id}
                        className={`platform-tab ${selected === p.id ? 'platform-tab--active' : ''} ${!p.active ? 'platform-tab--disabled' : ''}`}
                        onClick={() => p.active && onSelect(p.id)}
                        style={selected === p.id ? { '--tab-accent': p.color } : {}}
                    >
                        <span className="platform-tab__icon">{p.icon}</span>
                        <span className="platform-tab__label">{p.label}</span>
                        {!p.active && <span className="platform-tab__badge">Soon</span>}
                    </button>
                ))}
            </div>
        </div>
    );
}

export function ComingSoon({ platform }) {
    const info = PLATFORMS.find((p) => p.id === platform);
    return (
        <div className="coming-soon">
            <div className="coming-soon__icon">{info?.icon || '🔌'}</div>
            <h2 className="coming-soon__title">{info?.label || 'Platform'} Integration</h2>
            <p className="coming-soon__text">
                {info?.label} adapter is ready for connection. The ingestion pipeline,
                normalization layer, and analytics queries all support multi-platform data
                out of the box.
            </p>
            <div className="coming-soon__features">
                <div className="coming-soon__feature">✓ Adapter interface defined</div>
                <div className="coming-soon__feature">✓ Schema supports platform field</div>
                <div className="coming-soon__feature">✓ Analytics queries platform-aware</div>
                <div className="coming-soon__feature">○ API credentials needed</div>
            </div>
        </div>
    );
}
