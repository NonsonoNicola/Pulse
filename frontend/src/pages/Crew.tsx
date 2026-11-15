import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { TrafficLight } from '../components';
import type { CrewSummary, CrewFinding } from '../types';

export function Crew() {
  const { getCrewSummary } = useApi();
  const [summary, setSummary] = useState<CrewSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [locale, setLocale] = useState('en');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getCrewSummary(locale);
        setSummary(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [getCrewSummary, locale]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (!summary) return null;

  const levelOrder = ['red', 'orange', 'yellow', 'gray', 'green'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Crew Overview</h1>
          <p className="text-gray-400">Aggregated status — no individual data exposed</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={locale}
            onChange={e => setLocale(e.target.value)}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="en">English</option>
            <option value="it">Italiano</option>
          </select>
        </div>
      </div>

      {/* Level counts */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {levelOrder.map(level => {
          const count = summary.level_counts[level as keyof typeof summary.level_counts] || 0;
          const colors: Record<string, string> = {
            red: 'bg-red-500/20 border-red-500/30',
            orange: 'bg-orange-500/20 border-orange-500/30',
            yellow: 'bg-yellow-500/20 border-yellow-500/30',
            gray: 'bg-gray-500/20 border-gray-500/30',
            green: 'bg-green-500/20 border-green-500/30',
          };
          const textColors: Record<string, string> = {
            red: 'text-red-400',
            orange: 'text-orange-400',
            yellow: 'text-yellow-400',
            gray: 'text-gray-400',
            green: 'text-green-400',
          };
          return (
            <div key={level} className={`p-4 rounded-lg border ${colors[level]}`}>
              <div className="flex items-center justify-between">
                <span className={`font-medium ${textColors[level]}`}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>
                <span className="text-2xl font-bold font-mono">{count}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Crew Finding */}
      {summary.findings.length > 0 && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-bold">Crew Finding</h2>
          {summary.findings.map((finding: CrewFinding, idx: number) => (
            <div key={idx} className="space-y-3">
              <div className="p-4 bg-gray-700/50 rounded-lg">
                <p className="text-gray-300">{locale === 'en' ? finding.description_en : finding.description_it}</p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-gray-400">Confidence</p>
                  <p className="font-medium capitalize">{finding.confidence}</p>
                </div>
                <div>
                  <p className="text-gray-400">Coverage</p>
                  <p className="font-mono font-medium">{Math.round(finding.coverage * 100)}%</p>
                </div>
                <div>
                  <p className="text-gray-400">Members</p>
                  <p className="font-mono font-medium">{finding.member_count} / {summary.member_count}</p>
                </div>
                <div>
                  <p className="text-gray-400">Window</p>
                  <p className="font-mono font-medium">{finding.window_start} → {finding.window_end}</p>
                </div>
              </div>
              <div className="space-y-2">
                <p className="font-medium">Metrics involved:</p>
                <div className="flex flex-wrap gap-2">
                  {finding.metrics.map((m, i) => (
                    <span key={i} className="px-2 py-1 bg-gray-800 rounded text-xs">
                      {m.metric} ({m.direction}, Z={m.mean_z})
                    </span>
                  ))}
                </div>
              </div>
              {finding.env_correlations.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-gray-700">
                  <p className="font-medium">Environmental Correlations:</p>
                  <div className="grid md:grid-cols-3 gap-3 text-sm">
                    {finding.env_correlations.map((c, i) => (
                      <div key={i} className={`p-3 rounded-lg ${c.significant ? 'bg-green-500/10 border border-green-500/30' : 'bg-gray-800/50'}`}>
                        <p className="font-medium">{c.env_metric}</p>
                        <p className="font-mono">r = {c.r.toFixed(2)}</p>
                        <p className="text-gray-400">p = {c.p_value.toFixed(4)}</p>
                        <p className="text-gray-400">lag = {c.lag_days}d</p>
                        <p className={c.significant ? 'text-green-400' : 'text-gray-500'}>
                          {c.significant ? 'Significant' : 'Not significant'}
                        </p>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 text-center">Correlation is not causation</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Environmental Alerts */}
      {summary.environmental_alerts.length > 0 && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-bold">Environmental Alerts</h2>
          {summary.environmental_alerts.map((alert, idx) => (
            <div key={idx} className="p-4 bg-gray-700/50 rounded-lg flex items-center justify-between">
              <div>
                <p className="font-medium">{alert.explanation}</p>
                <p className="text-sm text-gray-400">{alert.metric}: {alert.value_text} (threshold: {alert.threshold_text})</p>
              </div>
              <TrafficLight level={alert.level} size="sm" showLabel={false} />
            </div>
          ))}
        </div>
      )}

      {/* Crew Goal */}
      {summary.crew_goal && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-bold">{locale === 'en' ? summary.crew_goal.label_en : summary.crew_goal.label_it}</h2>
          <div className="h-4 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${summary.crew_goal.reached ? 'bg-green-500' : 'bg-teal-500'}`}
              style={{ width: `${summary.crew_goal.value * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-sm text-gray-400">
            <span>{Math.round(summary.crew_goal.value * 100)}%</span>
            <span>Target: {Math.round(summary.crew_goal.target * 100)}%</span>
          </div>
          {summary.crew_goal.reached && (
            <p className="text-green-400 text-center">🎉 Crew goal achieved!</p>
          )}
        </div>
      )}
    </div>
  );
}