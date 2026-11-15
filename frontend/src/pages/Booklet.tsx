import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { TrafficLight, StatusBadge } from '../components';
import type { Astronaut } from '../types';

export function Booklet() {
  const { user } = useAuth();
  const { getBooklet, exportBooklet, getCrewMembers } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [booklet, setBooklet] = useState<{ profile: Astronaut; status: any; events: any[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [crew, setCrew] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    if (user?.role === 'astronaut') return;
    getCrewMembers().then(data => {
      if (data) setCrew(data as { id: string; name: string }[]);
    });
  }, [getCrewMembers, user?.role]);

  useEffect(() => {
    if (!user) return;
    if (user.role === 'astronaut') {
      if (user.astronaut_id) setAstronautId(user.astronaut_id);
      return;
    }
    if (crew.length > 0) {
      setAstronautId(prev => prev || crew[0].id);
    }
  }, [user, crew]);

  useEffect(() => {
    if (!astronautId) return;
    setLoading(true);
    getBooklet(astronautId).then(data => {
      setBooklet(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [astronautId, getBooklet]);

  const handleExport = async () => {
    if (!astronautId) return;
    setExporting(true);
    try {
      const blob = await exportBooklet(astronautId);
      if (!blob) throw new Error('Export failed');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `booklet_${astronautId}.zip`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const formatEvent = (event: any) => {
    const time = new Date(event.measured_at).toLocaleString();
    const quality = event.quality !== 'ok' ? ` ⚠️ ${event.quality}` : '';
    const payload = event.payload ? ` — ${JSON.stringify(event.payload).slice(0, 100)}` : '';
    return `${time} [${event.type}]${quality}${payload}`;
  };

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Medical Booklet</h1>
          <p className="text-gray-400">Timeline, reports, and export</p>
        </div>
        <div className="flex items-center gap-4">
          {user.role !== 'astronaut' && (
            <select
              value={astronautId}
              onChange={e => setAstronautId(e.target.value)}
              className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              <option value="">Select astronaut</option>
              {crew.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          )}
          {booklet && (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-gray-900 font-medium rounded-lg disabled:opacity-50"
            >
              {exporting ? 'Exporting...' : 'Export Booklet (ZIP)'}
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
        </div>
      )}

      {booklet && (
        <div className="space-y-6">
          {/* Profile */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
              <div>
                <h2 className="text-xl font-bold">{booklet.profile.name}</h2>
                <p className="text-gray-400">{booklet.profile.role_title}</p>
              </div>
              <div className="flex items-center gap-4">
                <TrafficLight level={booklet.status.level} size="sm" showLabel={false} />
                <StatusBadge level={booklet.status.level} compact />
              </div>
            </div>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-400">Confidence</p>
                <p className="font-medium capitalize">{booklet.status.confidence}</p>
              </div>
              <div>
                <p className="text-gray-400">Coverage (3d)</p>
                <p className="font-mono font-medium">{Math.round(booklet.status.coverage * 100)}%</p>
              </div>
              <div>
                <p className="text-gray-400">Last Computed</p>
                <p className="font-mono font-medium">{new Date(booklet.status.computed_at).toLocaleString()}</p>
              </div>
            </div>
          </div>

          {/* Baselines */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-bold mb-4">Personal Baselines</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="pb-2">Metric</th>
                    <th className="pb-2">Center</th>
                    <th className="pb-2">Spread</th>
                    <th className="pb-2">Origin</th>
                    <th className="pb-2">N</th>
                    <th className="pb-2">Frozen</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(booklet.status.baselines).map(([metric, baseline]: [string, any]) => (
                    <tr key={metric} className="border-b border-gray-700/50">
                      <td className="py-2 font-mono">{metric}</td>
                      <td className="py-2">{baseline.center.toFixed(1)}</td>
                      <td className="py-2">±{baseline.spread.toFixed(1)}</td>
                      <td className="py-2">{baseline.origin}</td>
                      <td className="py-2">{baseline.n_obs}</td>
                      <td className="py-2">{baseline.frozen ? '✓' : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-bold mb-4">Timeline (last 200 events)</h3>
            <div className="max-h-96 overflow-y-auto space-y-2 font-mono text-sm">
              {booklet.events.slice(0, 50).map((event, idx) => (
                <div key={idx} className={`py-1 px-2 rounded ${event.quality !== 'ok' ? 'bg-red-500/10 border-l-2 border-red-500' : 'hover:bg-gray-700/50'}`}>
                  {formatEvent(event)}
                </div>
              ))}
              {booklet.events.length > 50 && (
                <p className="text-gray-500 text-center py-2">... and {booklet.events.length - 50} more events</p>
              )}
            </div>
          </div>

          {/* Tests */}
          {(booklet.status.tests || []).length > 0 && (
            <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
              <h3 className="text-lg font-bold mb-4">Scheduled Tests</h3>
              <div className="space-y-2">
                {(booklet.status.tests || []).map((test: any, idx: number) => (
                  <div key={idx} className="p-3 bg-gray-700/50 rounded-lg flex items-center justify-between">
                    <div>
                      <p className="font-medium">{test.test.replace(/_/g, ' ')}</p>
                      <p className="text-sm text-gray-400">{test.why_en}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs rounded ${test.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                      {test.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}