import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { TrafficLight, StatusBadge } from '../components';
import type { Astronaut } from '../types';

export function Profile() {
  const { user, savePreferences } = useAuth();
  const { getStatus } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [astronaut, setAstronaut] = useState<Astronaut | null>(null);
  const [locale, setLocale] = useState(user?.locale || 'en');
  const [explanationLevel, setExplanationLevel] = useState(user?.explanation_level || 'simple');

  useEffect(() => {
    if (!astronautId) {
      if (user?.role === 'astronaut') setAstronautId(user.astronaut_id || '');
      else if (user?.role === 'cmo' || user?.role === 'ground' || user?.role === 'admin') {
        // Will be set when astronaut is selected
      }
    }
  }, [user]);

  useEffect(() => {
    if (astronautId) {
      getStatus(astronautId).then(setAstronaut);
    }
  }, [astronautId, getStatus]);

  const handleSavePreferences = async () => {
    try {
      await savePreferences({ locale, explanation_level: explanationLevel });
      alert('Preferences saved.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save preferences');
    }
  };

  const handleExportData = async () => {
    if (!astronautId) return;
    try {
      const res = await fetch(`/api/booklet/${astronautId}/export`, { credentials: 'include' });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `booklet_${astronautId}.zip`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      alert('Export failed');
    }
  };

  if (!user) return null;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Profile & Preferences</h1>

      {/* User Info */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
        <h2 className="text-xl font-bold mb-4">Account</h2>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-400">Username</p>
            <p className="font-mono">{user.username}</p>
          </div>
          <div>
            <p className="text-gray-400">Display Name</p>
            <p>{user.display_name}</p>
          </div>
          <div>
            <p className="text-gray-400">Role</p>
            <p className="capitalize">{user.role}</p>
          </div>
          <div>
            <p className="text-gray-400">Astronaut</p>
            <p>{astronaut?.name || '—'}</p>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-6">
        <h2 className="text-xl font-bold">Preferences</h2>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Language / Lingua</label>
          <select
            value={locale}
            onChange={e => setLocale(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="en">English</option>
            <option value="it">Italiano</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Explanation Level</label>
          <select
            value={explanationLevel}
            onChange={e => setExplanationLevel(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="simple">Simple — just what to do</option>
            <option value="detailed">Detailed — observations + hypotheses</option>
            <option value="clinical">Clinical — full technical detail</option>
          </select>
        </div>

        <button
          onClick={handleSavePreferences}
          className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-gray-900 font-medium rounded-lg"
        >
          Save Preferences
        </button>
      </div>

      {/* Astronaut Status (if linked) */}
      {astronaut && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">{astronaut.name}</h2>
              <p className="text-gray-400">{astronaut.role_title}</p>
            </div>
            <div className="flex items-center gap-2">
              <TrafficLight level={astronaut.level} size="sm" showLabel={false} />
              <StatusBadge level={astronaut.level} compact />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-gray-700/50 rounded-lg">
              <p className="text-gray-400">Confidence</p>
              <p className="font-medium capitalize">{astronaut.confidence}</p>
            </div>
            <div className="p-3 bg-gray-700/50 rounded-lg">
              <p className="text-gray-400">Coverage (3d)</p>
              <p className="font-mono font-medium">{Math.round(astronaut.coverage * 100)}%</p>
            </div>
            <div className="p-3 bg-gray-700/50 rounded-lg">
              <p className="text-gray-400">Honesty Streak</p>
              <p className="font-bold font-mono text-teal-400">{astronaut.gamification.honesty_days}</p>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-700">
            <button
              onClick={handleExportData}
              className="w-full py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 font-medium rounded-lg"
            >
              Export My Booklet (ZIP)
            </button>
          </div>
        </div>
      )}

      {/* Astronaut Selector (for non-astronaut roles) */}
      {!astronaut && user.role !== 'astronaut' && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
          <h2 className="text-xl font-bold mb-4">Select Astronaut to View</h2>
          <p className="text-gray-400 mb-4">Choose an astronaut to see their status and export options.</p>
          <div className="grid gap-2">
            {['astronaut_01', 'astronaut_02', 'astronaut_03', 'astronaut_04'].map(id => (
              <button
                key={id}
                onClick={() => setAstronautId(id)}
                className="p-4 bg-gray-700/50 rounded-lg border border-gray-700 hover:border-teal-500/50 text-left transition-colors"
              >
                <p className="font-medium">{id === 'astronaut_01' ? 'Elena Rossi' : id === 'astronaut_02' ? 'Maya Chen' : id === 'astronaut_03' ? 'Luca Bianchi' : 'Aiko Tanaka'}</p>
                <p className="text-sm text-gray-400">{id}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}