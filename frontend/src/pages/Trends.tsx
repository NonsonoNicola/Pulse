import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { TrafficLight, StatusBadge } from '../components';
import type { Astronaut } from '../types';

const METRIC_LABELS: Record<string, { label: string; unit: string }> = {
  resting_hr: { label: 'Resting HR', unit: 'bpm' },
  hrv_rmssd: { label: 'HRV', unit: 'ms' },
  spo2: { label: 'SpO₂', unit: '%' },
  skin_temp: { label: 'Skin Temp', unit: '°C' },
  respiratory_rate: { label: 'Resp Rate', unit: '/min' },
  sleep_hours: { label: 'Sleep', unit: 'h' },
  sleep_efficiency: { label: 'Sleep Eff.', unit: '%' },
  mood: { label: 'Mood', unit: '/5' },
  energy: { label: 'Energy', unit: '/5' },
  symptom_load: { label: 'Symptom Load', unit: 'score' },
  hydration: { label: 'Hydration', unit: '/5' },
  pain: { label: 'Pain', unit: '/10' },
  activity_min: { label: 'Activity', unit: 'min' },
};

function formatData(metric: string, trends: Record<string, unknown> | null) {
  const data = trends?.[metric] as { points: unknown[] } | undefined;
  if (!data?.points) return [];
  return data.points
    .filter((p: any) => p.value !== null && p.value !== undefined)
    .map((p: any) => ({
      date: p.date,
      value: p.value,
      quality: p.quality,
      backfilled: p.backfilled,
    }));
}

export function Trends() {
  const { user } = useAuth();
  const { getTrends, getStatus, getCrewMembers } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [astronaut, setAstronaut] = useState<Astronaut | null>(null);
  const [trends, setTrends] = useState<Record<string, unknown> | null>(null);
  const [days, setDays] = useState(30);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['resting_hr', 'hrv_rmssd', 'sleep_hours', 'spo2']);
  const [crew, setCrew] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    if (!astronautId) return;
    setLoading(true);
    try {
      const [status, trendsData] = await Promise.all([
        getStatus(astronautId),
        getTrends(astronautId, days),
      ]);
      setAstronaut(status);
      setTrends(trendsData as Record<string, unknown>);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'astronaut') return;
    getCrewMembers().then(data => {
      if (data) setCrew(data as { id: string; name: string }[]);
    });
  }, [getCrewMembers, user?.role]);

  useEffect(() => {
    if (astronautId) {
      loadData();
    }
  }, [astronautId, days, getStatus, getTrends]);

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

  if (!user) return null;

  const metricKeys = Object.keys(METRIC_LABELS);
  const availableMetrics = metricKeys.filter(m => trends && trends[m]);

  const renderCharts = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
        </div>
      );
    }

    if (!trends) {
      return (
        <div className="text-center text-gray-500 py-12">
          <p>No trend data available for selected astronaut</p>
        </div>
      );
    }

    return (
      <div className="grid gap-6 md:grid-cols-2">
        {selectedMetrics.map(metric => {
          const metricData = formatData(metric, trends);
          const meta = METRIC_LABELS[metric];
          const baseline = astronaut?.baselines?.[metric];
          return (
            <div key={metric} className="bg-gray-800/50 rounded-xl border border-gray-700 p-4 h-80">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">{meta.label} ({meta.unit})</h3>
                {baseline && (
                  <span className="text-xs text-gray-400 font-mono">
                    Baseline: {baseline.center.toFixed(1)} ± {baseline.spread.toFixed(1)} ({baseline.origin})
                  </span>
                )}
              </div>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metricData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={d => d.slice(5)}
                    tick={{ fill: '#6b7280', fontSize: 10 }}
                    stroke="#374151"
                  />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} stroke="#374151" />
                  <Tooltip content={renderCustomTooltip} />
                  <Legend />
                  {baseline && (
                    <>
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#5eead4"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                      <Line
                        type="monotone"
                        data={metricData.map(d => ({ ...d, baseline_center: baseline.center }))}
                        dataKey="baseline_center"
                        stroke="#6b7280"
                        strokeWidth={1}
                        strokeDasharray="4 4"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        data={metricData.map(d => ({ ...d, upper: baseline.center + baseline.spread }))}
                        dataKey="upper"
                        stroke="#6b7280"
                        strokeWidth={0.5}
                        strokeDasharray="2 2"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        data={metricData.map(d => ({ ...d, lower: baseline.center - baseline.spread }))}
                        dataKey="lower"
                        stroke="#6b7280"
                        strokeWidth={0.5}
                        strokeDasharray="2 2"
                        dot={false}
                      />
                    </>
                  )}
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#5eead4"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-teal-400" /> Value</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full border-2 border-dashed border-gray-500" /> Baseline ±1σ</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> Suspect</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Invalid</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full border-2 border-gray-500" /> Backfilled</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Trends</h1>
          <p className="text-gray-400">Personal baselines, quality flags, and backfilled data</p>
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
          {astronaut && (
            <div className="flex items-center gap-2">
              <TrafficLight level={astronaut.level} size="sm" showLabel={false} />
              <StatusBadge level={astronaut.level} compact />
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Time range:</label>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
          </select>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm text-gray-400">Metrics:</label>
          <div className="flex flex-wrap gap-1">
            {availableMetrics.map(m => (
              <label key={m} className="flex items-center gap-1 px-2 py-1 bg-gray-800 rounded text-xs cursor-pointer hover:bg-gray-700">
                <input
                  type="checkbox"
                  checked={selectedMetrics.includes(m)}
                  onChange={e => setSelectedMetrics(prev =>
                    e.target.checked ? [...prev, m] : prev.filter(x => x !== m)
                  )}
                  className="rounded border-gray-600 text-teal-500 focus:ring-teal-500"
                />
                <span className="text-gray-300">{METRIC_LABELS[m].label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {renderCharts()}
    </div>
  );
}

function renderCustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 p-3 rounded-lg shadow-lg">
      <p className="font-mono text-xs text-gray-400">{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: <span className="font-mono">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

export default Trends;