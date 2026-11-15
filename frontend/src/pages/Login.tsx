import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { roleHome } from '../utils/roles';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const logged = await login(username, password);
      const demo = new URLSearchParams(location.search).get('demo');
      const destination = `${roleHome(logged.role)}${demo ? `?demo=${encodeURIComponent(demo)}` : ''}`;
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const demoAccounts = [
    { username: 'elena', role: 'Astronaut (Commander)' },
    { username: 'maya', role: 'CMO' },
    { username: 'luca', role: 'Astronaut' },
    { username: 'aiko', role: 'Astronaut' },
    { username: 'ground', role: 'Flight Surgeon' },
    { username: 'admin', role: 'Admin' },
  ];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md bg-gray-900/90 backdrop-blur rounded-xl border border-gray-800 p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-teal-400">Pulse</h1>
          <p className="text-gray-400 mt-2">NASA Space Apps 2026</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded text-red-300 text-sm">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              placeholder="elena"
              required
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              placeholder="crewmd"
              required
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-teal-500 hover:bg-teal-400 text-gray-900 font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="mt-8 pt-6 border-t border-gray-800">
          <p className="text-xs text-gray-500 text-center mb-3">Demo accounts (password: <code className="text-teal-400">crewmd</code>)</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {demoAccounts.map(acc => (
              <div
                key={acc.username}
                className="flex items-center gap-2 p-2 bg-gray-800/50 rounded hover:bg-gray-800 cursor-pointer"
                onClick={() => { setUsername(acc.username); setPassword('crewmd'); }}
              >
                <span className="font-mono text-teal-400">{acc.username}</span>
                <span className="text-gray-500">{acc.role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}