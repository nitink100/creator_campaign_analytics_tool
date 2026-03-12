import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getToken, setToken as persistToken, setOnUnauthorized, getApiBase } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [initialized, setInitialized] = useState(false);

    const logout = useCallback(() => {
        persistToken(null);
        setUser(null);
    }, []);

    useEffect(() => {
        setOnUnauthorized(logout);
    }, [logout]);

    useEffect(() => {
        let cancelled = false;
        const token = getToken();
        if (!token) {
            setInitialized(true);
            return;
        }
        fetch(`${getApiBase()}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => {
                if (cancelled) return;
                if (!res.ok) {
                    persistToken(null);
                    setInitialized(true);
                    return;
                }
                return res.json();
            })
            .then((data) => {
                if (cancelled || !data) return;
                setUser({ id: data.id, email: data.email, role: data.role || 'user' });
            })
            .catch(() => {
                if (!cancelled) persistToken(null);
            })
            .finally(() => {
                if (!cancelled) setInitialized(true);
            });
        return () => { cancelled = true; };
    }, []);

    const login = useCallback(async (email, password, staySignedIn = false) => {
        const res = await fetch(`${getApiBase()}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, stay_signed_in: staySignedIn }),
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        persistToken(data.access_token);
        const meRes = await fetch(`${getApiBase()}/api/auth/me`, { headers: { Authorization: `Bearer ${data.access_token}` } });
        const me = await meRes.json();
        if (meRes.ok && me) {
            setUser({ id: me.id, email: me.email, role: me.role || 'user' });
        } else {
            setUser({ id: '', email: email.trim(), role: 'user' });
        }
        return data;
    }, []);

    const signup = useCallback(async (email, password, staySignedIn = false) => {
        const res = await fetch(`${getApiBase()}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, stay_signed_in: staySignedIn }),
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Signup failed');
        }
        persistToken(data.access_token);
        const meRes = await fetch(`${getApiBase()}/api/auth/me`, { headers: { Authorization: `Bearer ${data.access_token}` } });
        const me = await meRes.json();
        if (meRes.ok && me) {
            setUser({ id: me.id, email: me.email, role: me.role || 'user' });
        } else {
            setUser({ id: '', email: email.trim(), role: 'user' });
        }
        return data;
    }, []);

    const value = {
        user,
        initialized,
        login,
        signup,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
