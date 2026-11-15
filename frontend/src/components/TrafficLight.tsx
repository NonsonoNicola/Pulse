import type { Level } from '../types';

const LEVEL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  green: { label: 'Green — No alert-level pattern', color: '#22c55e', bg: 'bg-green-500/20' },
  yellow: { label: 'Yellow — Attention', color: '#eab308', bg: 'bg-yellow-500/20' },
  orange: { label: 'Orange — Clinical review soon', color: '#f97316', bg: 'bg-orange-500/20' },
  red: { label: 'Red — Emergency', color: '#ef4444', bg: 'bg-red-500/20' },
  gray: { label: 'Gray — Not enough data', color: '#9ca3af', bg: 'bg-gray-500/20' },
};

interface TrafficLightProps {
  level: Level;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function TrafficLight({ level, size = 'md', showLabel = true }: TrafficLightProps) {
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.gray;
  const sizes = {
    sm: 'w-3 h-3',
    md: 'w-5 h-5',
    lg: 'w-8 h-8',
  };
  const activeClasses: Record<string, string> = {
    green: 'bg-green-500 shadow-[0_0_8px_#22c55e]',
    yellow: 'bg-yellow-500 shadow-[0_0_8px_#eab308]',
    red: 'bg-red-500 shadow-[0_0_8px_#ef4444]',
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex flex-col items-center gap-1">
        {['green', 'yellow', 'red'].map(color => {
          const active =
            (level === 'green' && color === 'green') ||
            (level === 'yellow' && color === 'yellow') ||
            (level === 'orange' && color === 'yellow') ||
            (level === 'red' && color === 'red');
          return (
            <div
              key={color}
              className={`${sizes[size]} rounded-full transition-all duration-300 ${
                active ? `${activeClasses[color]} animate-pulse` : 'bg-gray-700'
              }`}
            />
          );
        })}
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-gray-300">{config.label}</span>
      )}
    </div>
  );
}

export function StatusBadge({ level, compact = false }: { level: Level; compact?: boolean }) {
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.gray;
  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${
        config.bg
      } ${compact ? 'px-1.5 py-0.5' : ''}`}
      style={{ color: config.color }}
    >
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}