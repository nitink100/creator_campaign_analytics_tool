import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './context/AuthContext';
import PlatformSelector, { ComingSoon } from './components/PlatformSelector';
import KPICards from './components/KPICards';
import CreatorLeaderboard from './components/CreatorLeaderboard';
import EngagementChart from './components/EngagementChart';
import TopContent from './components/TopContent';
import TimePeriodFilter from './components/TimePeriodFilter';
import SyncFooter from './components/SyncFooter';
import ChannelDiscovery from './components/ChannelDiscovery';
import Campaigns from './components/Campaigns';
import ConfirmModal from './components/ConfirmModal';
import Login from './components/Login';
import Signup from './components/Signup';
import { api } from './api/client';

export default function App() {
    const { user, initialized, logout } = useAuth();
    const [authTab, setAuthTab] = useState('login'); // 'login' | 'signup'
    const [platform, setPlatform] = useState('youtube');
    const [summary, setSummary] = useState(null);
    const [topCreators, setTopCreators] = useState([]);
    const [topContent, setTopContent] = useState([]);
    const [lastRun, setLastRun] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshKey, setRefreshKey] = useState(0);
    const [timePeriod, setTimePeriod] = useState(30);
    const [view, setView] = useState('dashboard'); // 'dashboard' or 'campaigns'
    const [confirmModal, setConfirmModal] = useState(null);
    const [profileOpen, setProfileOpen] = useState(false);
    const profileRef = useRef(null);

    useEffect(() => {
        if (!profileOpen) return;
        const close = (e) => {
            if (profileRef.current && !profileRef.current.contains(e.target)) setProfileOpen(false);
        };
        document.addEventListener('click', close);
        return () => document.removeEventListener('click', close);
    }, [profileOpen]);

    const showModal = useCallback((options) => {
        setConfirmModal(options);
    }, []);

    const hideModal = useCallback(() => {
        setConfirmModal(null);
    }, []);

    const loadDashboard = useCallback(async (days, silent = false) => {
        const d = days ?? timePeriod;
        if (!silent) setLoading(true);
        setError(null);
        try {
            const [summaryRes, creatorsRes, runsRes] = await Promise.all([
                api.getSummary(d),
                api.getTopCreators(50, d),
                api.getLastRun(),
            ]);
            setSummary(summaryRes.data);
            setTopCreators(creatorsRes.items || []);
            setLastRun(runsRes.items?.[0] || null);
        } catch (err) {
            setError(err.message);
        } finally {
            if (!silent) setLoading(false);
        }
    }, [timePeriod]);

    useEffect(() => {
        if (user) loadDashboard();
    }, [user, loadDashboard]);

    const handleTimePeriodChange = useCallback((days) => {
        setTimePeriod(days);
        loadDashboard(days);
    }, [loadDashboard]);

    const handleFullRefresh = useCallback(async (silent = false) => {
        if (!silent) setRefreshKey((k) => k + 1);
        await loadDashboard(undefined, silent);
    }, [loadDashboard]);

    const isYoutube = platform === 'youtube';

    if (!initialized) {
        return (
            <div className="auth-loading">
                <div className="spinner" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="auth-screen">
                {authTab === 'login' ? (
                    <Login onSwitchToSignup={() => setAuthTab('signup')} />
                ) : (
                    <Signup onSwitchToLogin={() => setAuthTab('login')} />
                )}
            </div>
        );
    }

    return (
        <>
            <header className={`dashboard-header ${view === 'campaigns' ? 'dashboard-header--campaigns' : ''}`}>
                <div className="header-row-1">
                    <div className="header-row-1-left">
                        {view === 'campaigns' ? (
                            <>
                                <h1 className="app-title">Campaigns</h1>
                                <span className="app-subtitle">Create and manage campaigns, and add creators to them.</span>
                            </>
                        ) : (
                            <>
                                <h1 className="app-title">Creator Dashboard</h1>
                                <span className="app-subtitle">Metrics and performance for your creators and their content.</span>
                            </>
                        )}
                    </div>
                    <div className="header-row-1-right">
                        <div className="header-mode-switcher" data-active={view}>
                            <div className="header-mode-switcher__thumb" aria-hidden="true" />
                            <nav className="main-nav main-nav--top">
                                <button 
                                    className={`nav-item ${view === 'dashboard' ? 'active' : ''}`}
                                    onClick={() => setView('dashboard')}
                                >
                                    Creator Dashboard
                                </button>
                                <button 
                                    className={`nav-item ${view === 'campaigns' ? 'active' : ''}`}
                                    onClick={() => setView('campaigns')}
                                >
                                    Campaigns
                                </button>
                            </nav>
                        </div>
                        <div className="header-account" ref={profileRef}>
                            {user?.role === 'admin' && (
                                <span className="auth-admin-badge" title="Administrator">Admin</span>
                            )}
                            <button
                                type="button"
                                className="profile-trigger"
                                onClick={(e) => { e.stopPropagation(); setProfileOpen((o) => !o); }}
                                title="Profile"
                                aria-expanded={profileOpen}
                                aria-haspopup="true"
                            >
                                <span className="profile-trigger__avatar" aria-hidden="true">
                                    {user?.email ? user.email.charAt(0).toUpperCase() : '?'}
                                </span>
                            </button>
                            {profileOpen && (
                                <div className="profile-dropdown" role="menu">
                                    <div className="profile-dropdown__email">{user?.email ?? '—'}</div>
                                    <button type="button" className="profile-dropdown__signout" onClick={() => { setProfileOpen(false); logout(); }} role="menuitem">
                                        Sign out
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                <div className="header-row-2">
                    <div className="header-row-2-left">
                        {view === 'dashboard' && (
                            <PlatformSelector selected={platform} onSelect={setPlatform} hideTitle />
                        )}
                    </div>
                    {view === 'dashboard' && isYoutube && (
                        <div className="header-row-2-right">
                            <TimePeriodFilter value={timePeriod} onChange={handleTimePeriodChange} />
                        </div>
                    )}
                </div>
            </header>

            <div className="dashboard">
                {error && (
                    <div className={error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? "offline-banner" : "error-banner"}>
                        <span>{error.toLowerCase().includes('connect') || error.toLowerCase().includes('backend is running') ? `Offline: ${error}` : `Failed to load dashboard: ${error}`}</span>
                        <button onClick={handleFullRefresh}>Retry</button>
                    </div>
                )}

                {view === 'campaigns' ? (
                    <Campaigns showModal={showModal} />
                ) : isYoutube ? (
                    <>
                        <KPICards summary={summary} loading={loading} />

                        {!loading && summary && summary.total_creators === 0 ? (
                            <div className="empty-state">
                                <h3>No Data Available</h3>
                                <p>Begin by discovering and tracking channels below.</p>
                            </div>
                        ) : (
                            <>
                                <div className="middle-section">
                                    <CreatorLeaderboard
                                        refreshKey={refreshKey}
                                        timePeriod={timePeriod}
                                        onFullRefresh={handleFullRefresh}
                                        showModal={showModal}
                                    />
                                    <EngagementChart creators={topCreators} loading={loading} />
                                </div>

                                <TopContent timePeriod={timePeriod} refreshKey={refreshKey} creators={topCreators} />
                            </>
                        )}

                        <ChannelDiscovery refreshKey={refreshKey} onChannelTracked={handleFullRefresh} />
                    </>
                ) : (
                    <ComingSoon platform={platform} />
                )}

                <SyncFooter
                    lastRun={lastRun}
                    summary={summary}
                    onSyncComplete={() => handleFullRefresh(false)}
                    onSilentPoll={() => handleFullRefresh(true)}
                    showModal={showModal}
                />
            </div>
            {confirmModal && (
                <ConfirmModal 
                    modal={confirmModal} 
                    onClose={hideModal} 
                />
            )}
        </>
    );
}
