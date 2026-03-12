import React, { useState } from 'react';
import { api } from '../api/client';

export default function AddChannel({ onAdded }) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);

    const handleAdd = async () => {
        const ids = input
            .split(/[\n,]+/)
            .map((s) => s.trim())
            .filter(Boolean);

        if (ids.length === 0) {
            setError('Enter at least one channel ID');
            return;
        }

        setLoading(true);
        setError(null);
        setMessage(null);
        try {
            const res = await api.addChannels(ids);
            setMessage(res.message);
            setInput('');
            if (onAdded) onAdded();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="panel add-channel">
            <div className="panel__header">
                <h2 className="panel__title">➕ Add YouTube Channels</h2>
            </div>
            <p className="add-channel__help">
                Paste YouTube channel IDs (comma or newline separated).
                Find a channel ID from any YouTube channel URL: <code>youtube.com/channel/<strong>UC...</strong></code>
            </p>
            <textarea
                className="add-channel__input"
                placeholder="UCX6OQ3DkcsbYNE6H8uQQuVA&#10;UCq-Fj5jknLsUf-MWSy4_brA"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={3}
            />
            <div className="add-channel__actions">
                <button className="sync-btn" onClick={handleAdd} disabled={loading}>
                    {loading ? 'Adding...' : 'Add Channels'}
                </button>
                {message && <span className="add-channel__msg success">{message}</span>}
                {error && <span className="add-channel__msg error">{error}</span>}
            </div>
        </div>
    );
}
