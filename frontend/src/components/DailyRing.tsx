import type { GamificationState } from '../types';

interface DailyRingProps {
  gamification: GamificationState;
  size?: number;
  strokeWidth?: number;
}

export function DailyRing({ gamification, size = 80, strokeWidth = 8 }: DailyRingProps) {
  const { daily_ring, test_today } = gamification;
  const segments = [
    { key: 'checkin', label: 'Check-in', done: daily_ring.checkin },
    { key: 'test', label: test_today ? `Test: ${test_today.replace(/_/g, ' ')}` : 'No test today', done: daily_ring.test },
  ];
  const completed = segments.filter(s => s.done).length;
  const total = segments.length;
  const progress = total > 0 ? completed / total : 0;
  const circumference = 2 * Math.PI * (size / 2 - strokeWidth);
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - strokeWidth}
          fill="none"
          stroke="#374151"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - strokeWidth}
          fill="none"
          stroke="#5eead4"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500"
        />
      </svg>
      <div className="text-center">
        <p className="text-xs text-gray-400">Daily Ring</p>
        <p className="text-sm font-mono text-gray-200">{completed}/{total}</p>
      </div>
      <div className="flex gap-2 text-xs text-gray-400">
        {segments.map((s) => (
          <span key={s.key} className={`flex items-center gap-1 ${s.done ? 'text-green-400' : 'text-gray-500'}`}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: s.done ? '#22c55e' : '#374151' }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}