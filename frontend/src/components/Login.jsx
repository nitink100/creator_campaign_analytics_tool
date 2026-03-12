import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

export default function Login({ onSwitchToSignup }) {
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [staySignedIn, setStaySignedIn] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email.trim(), password, staySignedIn);
        } catch (err) {
            setError(err.message || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-card">
            <h1 className="auth-title">Sign in</h1>
            <p className="auth-subtitle">Creator Campaign Analytics</p>
            <form onSubmit={handleSubmit} className="auth-form">
                {error && <p className="auth-error">{error}</p>}
                <div className="auth-field">
                    <label htmlFor="login-email">Email</label>
                    <input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        placeholder="you@example.com"
                    />
                </div>
                <div className="auth-field">
                    <label htmlFor="login-password">Password</label>
                    <input
                        id="login-password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>
                <label className="auth-checkbox">
                    <input
                        type="checkbox"
                        checked={staySignedIn}
                        onChange={(e) => setStaySignedIn(e.target.checked)}
                    />
                    <span>Stay signed in</span>
                </label>
                <button type="submit" className="auth-submit" disabled={loading}>
                    {loading ? 'Signing in…' : 'Sign in'}
                </button>
                <p className="auth-switch">
                    Don’t have an account?{' '}
                    <button type="button" className="auth-link" onClick={onSwitchToSignup}>
                        Sign up
                    </button>
                </p>
            </form>
        </div>
    );
}
