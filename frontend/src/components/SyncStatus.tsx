import type { LinkStatus } from '../types';

const MODE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  live: { label: 'Live', color: '#22c55e', bg: 'bg-green-500/20' },
  async: { label: 'Async', color: '#eab308', bg: 'bg-yellow-500/20' },
  assisted: { label: 'Assisted', color: '#f97316', bg: 'bg-orange-500/20' },
  full: { label: 'Full Autonomy', color: '#ef4444', bg: 'bg-red-500/20' },
};

interface SyncStatusProps {
  status: LinkStatus | null;
  onConfigChange?: (rtt: number) => void;
  inline?: boolean;
}

export function SyncStatus({ status, onConfigChange, inline = false }: SyncStatusProps) {
  if (!status) return null;

  const config = MODE_CONFIG[status.mode] || MODE_CONFIG.full;

  return (
    <div
      className={
        inline
          ? 'flex items-center gap-2 flex-wrap'
          : 'fixed top-4 right-4 z-50 flex items-center gap-2 px-3 py-2 bg-gray-900/90 backdrop-blur rounded-lg border border-gray-700 shadow-lg'
      }
    >
      <div className="flex items-center gap-2">
        <span
          className={`px-2 py-1 text-xs font-semibold rounded ${config.bg}`}
          style={{ color: config.color }}
        >
          {config.label}
        </span>
        <span className="text-xs text-gray-400 font-mono">{status.rtt_seconds.toFixed(0)}s RTT</span>
      </div>
      {onConfigChange && (
        <select
          value={Math.round(status.rtt_seconds)}
          onChange={e => onConfigChange(Number(e.target.value))}
          className="ml-2 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-100"
        >
          <option value={5}>Live (5s)</option>
          <option value={60}>Async (1m)</option>
          <option value={300}>Async (5m)</option>
          <option value={1800}>Async (30m)</option>
          <option value={3600}>Assisted (1h)</option>
          <option value={21600}>Assisted (6h)</option>
          <option value={86400}>Full (1d)</option>
        </select>
      )}
    </div>
  );
}