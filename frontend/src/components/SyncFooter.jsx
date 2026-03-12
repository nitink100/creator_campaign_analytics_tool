import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { timeAgo } from '../utils/formatters';

export default function SyncFooter({ lastRun, summary, onSyncComplete, onSilentPoll, showModal }) {
    const { user } = useAuth();
    const isAdmin = user?.role === 'admin';
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState(null);

    const TERMINAL_STATUSES = ['success', 'failed', 'partial_success'];
    const POLL_INTERVAL_MS = 3000;
    const POLL_TIMEOUT_MS = 10 * 60 * 1000; // 10 min safety

    const handleSync = async () => {
        setSyncing(true);
        setError(null);
        try {
            const res = await api.triggerSync();
            const runId = res?.data?.id;
            if (runId) {
                const started = Date.now();
                while (Date.now() - started < POLL_TIMEOUT_MS) {
                    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
                    try {
                        const runRes = await api.getRun(runId);
                        const status = runRes?.data?.status;
                        if (status && TERMINAL_STATUSES.includes(status)) {
                            if (onSilentPoll) onSilentPoll();
                            else if (onSyncComplete) await onSyncComplete();
                            return;
                        }
                    } catch (_) {
                        // keep polling
                    }
                }
                // Timeout: refresh once so UI can show stale/retry
                if (onSilentPoll) onSilentPoll();
                else if (onSyncComplete) await onSyncComplete();
            } else {
                if (onSyncComplete) await onSyncComplete();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setSyncing(false);
        }
    };

    const handleReset = () => {
        showModal({
            title: 'Wipe System Data',
            message: 'DANGER: This will wipe all system data. Are you sure?',
            confirmText: 'Reset Data',
            danger: true,
            onConfirm: async () => {
                setSyncing(true);
                setError(null);
                try {
                    await api.resetDatabase();
                    if (onSyncComplete) await onSyncComplete();
                } catch (err) {
                    setError(err.message);
                } finally {
                    setSyncing(false);
                }
            }
        });
    };


    const lastSyncTime = lastRun?.finished_at;
    const isRunning = lastRun?.status === 'running' || lastRun?.status === 'pending';
    const isError = lastRun?.status === 'failed';
    // A run is "stale" if it's been running/pending for more than 5 minutes without update
    // (This is a frontend safety check)
    const isStale = isRunning && lastRun?.started_at && 
        (new Date() - new Date(lastRun.started_at)) > 5 * 60 * 1000;

    const displaySyncing = syncing || (isRunning && !isStale);
    const creatorsCount = summary?.total_creators ?? 0;
    const contentCount = summary?.total_content_items ?? 0;

    React.useEffect(() => {
        let intervalId;
        if (isRunning) {
            intervalId = setInterval(() => {
                if (onSilentPoll) onSilentPoll();
                else if (onSyncComplete) onSyncComplete();
            }, 3000); // poll every 3 seconds while running
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [isRunning, onSyncComplete, onSilentPoll]);

    return (
        <div className="sync-footer">
            <div className="sync-status">
                {isRunning ? (
                    <>
                        <div className={`pulse-icon ${isStale ? 'stale' : ''}`} />
                        <span>{isStale ? 'Sync may be stuck...' : 'Syncing Data...'}</span>
                    </>
                ) : (
                    <>
                        <span className={`status-dot ${isError ? 'error' : ''}`} />
                        <span>{lastSyncTime ? `Last synced: ${timeAgo(lastSyncTime)}` : 'Never synced'}</span>
                    </>
                )}
                {error && <span style={{ color: 'var(--red)', marginLeft: 8 }}> — {error}</span>}
                {isAdmin && isStale && <button onClick={handleSync} style={{ marginLeft: 8, fontSize: '10px', padding: '2px 8px' }}>Force Retry</button>}
                {lastRun?.error_summary && !isStale && <span style={{ color: 'var(--red)', marginLeft: 8 }}> — {lastRun.error_summary}</span>}
            </div>

            <div className="platform-pill">
                <span className="yt-icon">▶</span>
                YOUTUBE: {creatorsCount} CREATORS, {contentCount} VIDEOS
            </div>

            <div className="sync-footer__actions" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                {isAdmin ? (
                    <>
                        <button
                            className="sync-btn reset-btn"
                            onClick={handleReset}
                            disabled={displaySyncing}
                            style={{ border: '1px solid #ff4444', color: '#ff4444', background: '#ffebeb', padding: '6px 16px', borderRadius: '4px', cursor: 'pointer' }}
                        >
                            {displaySyncing ? '⟳...' : '🗑 Reset Data'}
                        </button>
                        <button className="sync-btn" onClick={handleSync} disabled={displaySyncing}>
                            {displaySyncing ? '⟳ Syncing...' : '⟳ Sync Now'}
                        </button>
                    </>
                ) : (
                    <span className="sync-footer__admin-only">Sync and reset are restricted to admins.</span>
                )}
            </div>
        </div>
    );
}
