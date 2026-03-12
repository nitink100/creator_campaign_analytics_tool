// In production (e.g. Vercel), set VITE_API_URL to your backend (e.g. https://your-api.onrender.com)
const BASE = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
    : '';

export function getApiBase() {
    return BASE;
}

const AUTH_TOKEN_KEY = 'auth_token';

let _token = typeof localStorage !== 'undefined' ? localStorage.getItem(AUTH_TOKEN_KEY) : null;
let _onUnauthorized = () => {};

export function getToken() {
    return _token;
}

export function setToken(token) {
    _token = token;
    if (typeof localStorage !== 'undefined') {
        if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
        else localStorage.removeItem(AUTH_TOKEN_KEY);
    }
}

export function setOnUnauthorized(fn) {
    _onUnauthorized = fn;
}

async function request(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (_token) headers['Authorization'] = `Bearer ${_token}`;

    let res;
    try {
        res = await fetch(`${BASE}${url}`, {
            ...options,
            headers,
        });
    } catch (err) {
        throw new Error("Unable to connect to the server. Please check if the backend is running.");
    }

    if (res.status === 401) {
        _onUnauthorized();
        throw new Error("Session expired. Please sign in again.");
    }

    let data;
    try {
        data = await res.json();
    } catch (err) {
        if (!res.ok) {
            throw new Error(`Server returned an error (${res.status}). Ensure the backend is running.`);
        }
        throw new Error("Received invalid data from the server.");
    }

    if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        if (typeof data?.detail === 'string') {
            msg = data.detail;
        } else if (data?.detail?.message) {
            msg = data.detail.message;
        } else if (data?.message) {
            msg = data.message;
        }
        throw new Error(msg);
    }

    return data;
}

export const api = {
    getSummary: (days = 0) => request(`/api/analytics/summary?days=${days}`),
    getTopCreators: (limit = 50, days = 0) =>
        request(`/api/analytics/top-creators?limit=${limit}&days=${days}`),
    getTopContent: (limit = 50, days = 0, creatorName = null) => {
        let url = `/api/analytics/top-content?limit=${limit}&days=${days}`;
        if (creatorName) url += `&creator_name=${encodeURIComponent(creatorName)}`;
        return request(url);
    },
    getCreators: (params = {}) => {
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '') qs.set(k, v);
        });
        return request(`/api/creators?${qs.toString()}`);
    },
    getLastRun: () => request('/api/ingestion/runs?limit=1'),
    getRun: (runId) => request(`/api/ingestion/runs/${runId}`),
    triggerSync: () =>
        request('/api/ingestion/run', {
            method: 'POST',
            body: JSON.stringify({
                platform: 'youtube',
                source_type: 'api',
                trigger_type: 'manual',
            }),
        }),
    getChannels: () => request('/api/ingestion/channels'),
    resolveChannel: (query) =>
        request('/api/ingestion/channels/resolve', {
            method: 'POST',
            body: JSON.stringify({ query }),
        }),
    searchChannels: (q, limit = 5) =>
        request(`/api/ingestion/channels/search?q=${encodeURIComponent(q)}&limit=${limit}`),
    getCategories: (region = 'US') =>
        request(`/api/ingestion/categories?region=${region}`),
    getTrending: (categoryId, region = 'US', limit = 30) =>
        request(`/api/ingestion/trending?category_id=${categoryId}&region=${region}&limit=${limit}`),
    trackChannel: (channelId) =>
        request('/api/ingestion/channels/track', {
            method: 'POST',
            body: JSON.stringify({ channel_id: channelId }),
        }),
    untrackChannels: (channelIds) =>
        request('/api/ingestion/channels/untrack', {
            method: 'POST',
            body: JSON.stringify({ channel_ids: channelIds }),
        }),
    getQuota: () => request('/api/ingestion/quota'),
    resetDatabase: () => request('/api/admin/reset-db', { method: 'POST' }),

    // Campaigns
    getCampaigns: () => request('/api/campaigns'),
    createCampaign: (data) =>
        request('/api/campaigns', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
    getCampaign: (id) => request(`/api/campaigns/${id}`),
    updateCampaign: (id, data) =>
        request(`/api/campaigns/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),
    deleteCampaign: (id) => request(`/api/campaigns/${id}`, { method: 'DELETE' }),
    addCreatorToCampaign: (campaignId, creatorProfileId) =>
        request(`/api/campaigns/${campaignId}/members`, {
            method: 'POST',
            body: JSON.stringify({ creator_profile_id: creatorProfileId }),
        }),
    removeCreatorFromCampaign: (campaignId, creatorId) =>
        request(`/api/campaigns/${campaignId}/members/${creatorId}`, {
            method: 'DELETE',
        }),
};
