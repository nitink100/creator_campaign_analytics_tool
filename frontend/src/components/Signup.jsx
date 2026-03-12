import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

export default function Signup({ onSwitchToLogin }) {
    const { signup } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [staySignedIn, setStaySignedIn] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirm) {
            setError('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        setLoading(true);
        try {
            await signup(email.trim(), password, staySignedIn);
        } catch (err) {
            setError(err.message || 'Sign up failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-card">
            <h1 className="auth-title">Create account</h1>
            <p className="auth-subtitle">Creator Campaign Analytics</p>
            <form onSubmit={handleSubmit} className="auth-form">
                {error && <p className="auth-error">{error}</p>}
                <div className="auth-field">
                    <label htmlFor="signup-email">Email</label>
                    <input
                        id="signup-email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        placeholder="you@example.com"
                    />
                </div>
                <div className="auth-field">
                    <label htmlFor="signup-password">Password</label>
                    <input
                        id="signup-password"
                        type="password"
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
                        placeholder="At least 8 characters"
                    />
                </div>
                <div className="auth-field">
                    <label htmlFor="signup-confirm">Confirm password</label>
                    <input
                        id="signup-confirm"
                        type="password"
                        autoComplete="new-password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        required
                        minLength={8}
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
                    {loading ? 'Creating account…' : 'Sign up'}
                </button>
                <p className="auth-switch">
                    Already have an account?{' '}
                    <button type="button" className="auth-link" onClick={onSwitchToLogin}>
                        Sign in
                    </button>
                </p>
            </form>
        </div>
    );
}
