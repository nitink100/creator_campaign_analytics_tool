import React from 'react';

const PRESETS = [
    { label: '7D', days: 7 },
    { label: '30D', days: 30 },
    { label: '60D', days: 60 },
    { label: '90D', days: 90 },
];

export default function TimePeriodFilter({ value, onChange }) {
    return (
        <div className="time-filter">
            {PRESETS.map((p) => (
                <button
                    key={p.days}
                    className={`time-filter__pill${value === p.days ? ' active' : ''}`}
                    onClick={() => onChange(p.days)}
                >
                    {p.label}
                </button>
            ))}
        </div>
    );
}
