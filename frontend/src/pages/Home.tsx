import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { TrafficLight, StatusBadge, DailyRing } from '../components';
import type { Astronaut } from '../types';

export function Home() {
  const { user } = useAuth();
  const { getStatus, loading } = useApi();
  const [status, setStatus] = useState<Astronaut | null>(null);

  useEffect(() => {
    if (!user?.astronaut_id) return;
    getStatus(user.astronaut_id).then(data => {
      if (data) setStatus(data);
    });
  }, [user?.astronaut_id, getStatus]);

  if (!user?.astronaut_id) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">Select an astronaut to view their status</p>
      </div>
    );
  }

  if (loading || !status) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with traffic light */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{status.name}</h1>
          <p className="text-gray-400">{status.role_title}</p>
        </div>
        <div className="flex items-center gap-4">
          <TrafficLight level={status.level} size="lg" />
          <div className="text-right">
            <StatusBadge level={status.level} />
            <p className="text-xs text-gray-400 mt-1">{status.confidence} confidence</p>
          </div>
        </div>
      </div>

      {/* Primary reason */}
      <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <p className="text-gray-300">{status.primary_reason}</p>
      </div>

      {/* Daily ring + gamification */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="md:col-span-2 space-y-4">
          <DailyRing gamification={status.gamification} size={120} />
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-800/50 rounded-lg">
              <p className="text-xs text-gray-400">Honesty Streak</p>
              <p className="text-2xl font-bold font-mono text-teal-400">{status.gamification.honesty_days}</p>
              <p className="text-xs text-gray-400">{status.gamification.honesty_days_last_30} / 30 days</p>
            </div>
            <div className="p-4 bg-gray-800/50 rounded-lg">
              <p className="text-xs text-gray-400">Time Saved (7d)</p>
              <p className="text-2xl font-bold font-mono text-teal-400">{status.gamification.time_saved_minutes_7d} min</p>
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-xs text-gray-400">Crew Goal</p>
            <div className="mt-2">
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-teal-400 transition-all"
                  style={{ width: `${status.gamification.crew_goal.value * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {Math.round(status.gamification.crew_goal.value * 100)}% / {Math.round(status.gamification.crew_goal.target * 100)}%
              </p>
            </div>
          </div>
          {status.gamification.sentinel && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <p className="text-amber-400 text-sm font-medium">Sentinel Badge</p>
              <p className="text-xs text-gray-400 mt-1">{status.gamification.sentinel.text_en}</p>
            </div>
          )}
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-xs text-gray-400">Today's Task</p>
            <p className="text-lg font-medium text-teal-400 mt-1">
              {status.gamification.test_today
                ? status.gamification.test_today.replace(/_/g, ' ')
                : 'Check-in'}
            </p>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <a href="/checkin" className="block p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-teal-500/50 transition-colors text-center">
          <p className="text-xs text-gray-400">Check-in</p>
          <p className="font-medium mt-1">60 sec</p>
        </a>
        <a href="/chat" className="block p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-teal-500/50 transition-colors text-center">
          <p className="text-xs text-gray-400">Chat</p>
          <p className="font-medium mt-1">Ask anything</p>
        </a>
        <a href="/trends" className="block p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-teal-500/50 transition-colors text-center">
          <p className="text-xs text-gray-400">Trends</p>
          <p className="font-medium mt-1">View charts</p>
        </a>
        <a href="/emergency" className="block p-4 bg-red-500/10 border border-red-500/30 rounded-lg hover:border-red-500/50 transition-colors text-center">
          <p className="text-xs text-red-400">Emergency</p>
          <p className="font-medium mt-1">Protocol</p>
        </a>
      </div>
    </div>
  );
}