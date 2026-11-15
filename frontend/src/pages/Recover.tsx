import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { TrafficLight, StatusBadge } from '../components';
import type { Astronaut } from '../types';

export function Recover() {
  const { user } = useAuth();
  const { getStatus, getEvents, runScenario, getCrewMembers } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [astronaut, setAstronaut] = useState<Astronaut | null>(null);
  const [loading, setLoading] = useState(false);
  const [backfilling, setBackfilling] = useState<string | null>(null);
  const [heatmap, setHeatmap] = useState<Record<string, { hasData: boolean; backfilled: boolean }>>({});
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

  const loadAstronaut = async (id: string) => {
    const data = await getStatus(id);
    setAstronaut(data);
    const events = await getEvents(id, 1000);
    buildHeatmap((events || []) as any[]);
  };

  useEffect(() => {
    if (astronautId) {
      void loadAstronaut(astronautId);
    }
  }, [astronautId, getStatus, getEvents]);

  const buildHeatmap = (events: any[]) => {
    const map: Record<string, { hasData: boolean; backfilled: boolean }> = {};
    const today = new Date();
    for (let i = 59; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const key = date.toISOString().slice(0, 10);
      map[key] = { hasData: false, backfilled: false };
    }
    for (const event of events) {
      const measured = event?.measured_at ? String(event.measured_at) : '';
      const key = measured.slice(0, 10);
      if (!map[key]) continue;
      map[key].hasData = true;
      const recorded = event?.recorded_at ? Date.parse(event.recorded_at) : 0;
      const at = event?.measured_at ? Date.parse(event.measured_at) : 0;
      if (recorded && at && recorded - at > 60 * 60 * 1000) {
        map[key].backfilled = true;
      }
    }
    setHeatmap(map);
  };

  const handleBackfill = async (demoKey: 'S3' | 'S5') => {
    if (!astronautId) return;
    setBackfilling(demoKey);
    setLoading(true);
    try {
      const result = await runScenario(demoKey, demoKey === 'S3' ? 'backfill' : 'recheck');
      if (!result) throw new Error(`Could not run ${demoKey}`);
      alert(`${demoKey} backfill completed`);
      await loadAstronaut(astronautId);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Backfill failed');
    } finally {
      setLoading(false);
      setBackfilling(null);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Recover Lost Days</h1>
          <p className="text-gray-400">Backfill missed check-ins and sensor data</p>
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
        </div>
      </div>

      {astronaut && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">{astronaut.name}</h2>
              <p className="text-gray-400">Coverage (3d): {Math.round(astronaut.coverage * 100)}% | Honesty streak: {astronaut.gamification.honesty_days} days</p>
            </div>
            <div className="flex items-center gap-2">
              <TrafficLight level={astronaut.level} size="sm" showLabel={false} />
              <StatusBadge level={astronaut.level} compact />
            </div>
          </div>

          {/* Heatmap Calendar */}
          <div>
            <h3 className="text-lg font-bold mb-4">Last 60 Days — Check-in Coverage</h3>
            <div className="grid grid-cols-7 gap-1">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                <div key={d} className="text-center text-xs text-gray-500 py-1">{d}</div>
              ))}
              {Object.entries(heatmap).map(([date, data]) => (
                <div
                  key={date}
                  className={`aspect-square rounded flex items-center justify-center text-xs font-mono transition-colors ${
                    data.backfilled
                      ? 'bg-amber-500/30 border border-amber-500/50 text-amber-300'
                      : data.hasData
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-gray-700 text-gray-500'
                  }`}
                  title={formatDate(date)}
                >
                  {new Date(date).getDate()}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500/20" /> Has data</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-500/30 border border-amber-500/50" /> Backfilled</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-700" /> Missing</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid md:grid-cols-2 gap-4 pt-4 border-t border-gray-700">
            <button
              onClick={() => handleBackfill('S3')}
              disabled={loading || backfilling === 'S3'}
              className="p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-teal-500/50 transition-colors text-left disabled:opacity-50"
            >
              <p className="font-medium text-teal-400">S3 — Backfill Blackout Days</p>
              <p className="text-sm text-gray-400 mt-1">Inject 3 days of missed check-ins and vitals for Luca (or selected astronaut)</p>
              {backfilling === 'S3' && <p className="text-xs text-teal-400 mt-2">Injecting...</p>}
            </button>
            <button
              onClick={() => handleBackfill('S5')}
              disabled={loading || backfilling === 'S5'}
              className="p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-teal-500/50 transition-colors text-left disabled:opacity-50"
            >
              <p className="font-medium text-teal-400">S5 — Sensor Recheck</p>
              <p className="text-sm text-gray-400 mt-1">Add manual SpO₂ recheck for Aiko (or selected astronaut)</p>
              {backfilling === 'S5' && <p className="text-xs text-teal-400 mt-2">Injecting...</p>}
            </button>
          </div>

          {/* Honesty Streak */}
          <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
            <h4 className="font-medium mb-2">Honesty Streak</h4>
            <div className="flex items-center gap-4 text-sm">
              <div>
                <p className="text-gray-400">Total days</p>
                <p className="font-bold font-mono text-teal-400">{astronaut.gamification.honesty_days}</p>
              </div>
              <div>
                <p className="text-gray-400">Last 30 days</p>
                <p className="font-bold font-mono text-teal-400">{astronaut.gamification.honesty_days_last_30}</p>
              </div>
              <div>
                <p className="text-gray-400">Time saved (7d)</p>
                <p className="font-bold font-mono text-teal-400">{astronaut.gamification.time_saved_minutes_7d} min</p>
              </div>
              <p className="text-xs text-gray-500 mt-2">{astronaut.gamification.honesty_note_en}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}