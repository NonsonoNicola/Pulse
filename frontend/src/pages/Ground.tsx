import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { SyncStatus } from '../components';
import { TrafficLight, StatusBadge } from '../components';
import type { Case, LinkStatus } from '../types';

export function Ground() {
  const { user } = useAuth();
  const { getLinkStatus, getSyncQueue, flushSync, setLinkConfig } = useApi();

  const [cases, setCases] = useState<Case[]>([]);
  const [syncQueue, setSyncQueue] = useState<any[]>([]);
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [replyText, setReplyText] = useState('');
  const [loading, setLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);

  const fetchCases = async () => {
    try {
      const res = await fetch('/api/emergency/cases', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCases(data);
        setSelectedCase(prev => (prev ? data.find((c: Case) => c.id === prev.id) || null : null));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchSyncQueue = async () => {
    try {
      const data = await getSyncQueue();
      if (data) setSyncQueue(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLinkStatus = async () => {
    try {
      const data = await getLinkStatus();
      if (data) setLinkStatus(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchCases();
    fetchSyncQueue();
    fetchLinkStatus();
    const interval = setInterval(() => {
      fetchCases();
      fetchSyncQueue();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleFlush = async () => {
    setSyncLoading(true);
    try {
      await flushSync();
      fetchSyncQueue();
    } catch (err) {
      alert('Flush failed');
    } finally {
      setSyncLoading(false);
    }
  };

  const handleReply = async (caseId: string) => {
    if (!replyText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/emergency/cases/${caseId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ case_id: caseId, text: replyText, priority: 1 }),
      });
      if (res.ok) {
        setReplyText('');
        await fetchCases();
      } else {
        const detail = await res.json().catch(() => null);
        alert(detail?.detail || 'Reply failed');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Reply failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLinkChange = async (rtt: number) => {
    const updated = await setLinkConfig(rtt);
    if (updated) {
      setLinkStatus(updated);
    } else {
      alert('Link configuration requires the ground or admin role.');
    }
  };

  if (!user || !['ground', 'admin'].includes(user.role)) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Access restricted to Ground and Admin</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Ground Console</h1>
          <p className="text-gray-400">Flight surgeon dashboard — cases, sync queue, link status</p>
        </div>
        <SyncStatus status={linkStatus} onConfigChange={handleLinkChange} />
      </div>

      {/* Cases */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Open Cases</h2>
          <button onClick={fetchCases} disabled={loading} className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded">
            Refresh
          </button>
        </div>
        {cases.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No open cases</p>
        ) : (
          <div className="space-y-3">
            {cases.map(c => (
              <button
                key={c.id}
                onClick={() => setSelectedCase(c)}
                className={`w-full p-4 rounded-lg border text-left transition-colors ${
                  selectedCase?.id === c.id
                    ? 'bg-teal-500/10 border-teal-500/30 ring-1 ring-teal-500/20'
                    : 'bg-gray-700/50 border-gray-700 hover:border-teal-500/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-bold">{c.title}</p>
                    <p className="text-sm text-gray-400">{c.astronaut_id} • {c.protocol_id}</p>
                    <p className="text-xs text-gray-500">Opened: {new Date(c.opened_at).toLocaleString()}</p>
                  </div>
                  <TrafficLight level={c.level as any} size="sm" showLabel={false} />
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Case Detail */}
        {selectedCase && (
          <div className="mt-6 p-4 bg-gray-700/50 rounded-lg border border-gray-600 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold">Case Details</h3>
              <button onClick={() => setSelectedCase(null)} className="text-gray-400 hover:text-gray-200">Close</button>
            </div>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div><p className="text-gray-400">Case ID</p><p className="font-mono">{selectedCase.id}</p></div>
              <div><p className="text-gray-400">Astronaut</p><p>{selectedCase.astronaut_id}</p></div>
              <div><p className="text-gray-400">Level</p><p><StatusBadge level={selectedCase.level as any} compact /></p></div>
              <div><p className="text-gray-400">Protocol</p><p>{selectedCase.protocol_id}</p></div>
              <div><p className="text-gray-400">Status</p><p className="capitalize">{selectedCase.status}</p></div>
              <div><p className="text-gray-400">Opened</p><p>{new Date(selectedCase.opened_at).toLocaleString()}</p></div>
            </div>

            {/* SBAR Packets */}
            {selectedCase.sbar_ids && selectedCase.sbar_ids.length > 0 && (
              <div className="pt-4 border-t border-gray-700">
                <h4 className="font-medium mb-2">SBAR Packets</h4>
                <div className="space-y-2">
                  {selectedCase.sbar_ids.map((sbarId: string, idx: number) => (
                    <div key={idx} className="p-3 bg-gray-800 rounded-lg text-sm">
                      <p className="font-mono">{sbarId}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="pt-4 border-t border-gray-700">
              <h4 className="font-medium mb-2">Notes & Ground Replies</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {selectedCase.notes?.map((note: any, idx: number) => (
                  <div key={idx} className={`p-3 rounded-lg ${note.from_ground ? 'bg-blue-500/10 border border-blue-500/30' : 'bg-gray-800/50'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">{new Date(note.at).toLocaleString()}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${note.priority >= 3 ? 'bg-red-500/20 text-red-400' : 'bg-gray-600 text-gray-300'}`}>
                        Priority {note.priority}
                      </span>
                    </div>
                    <p className="mt-1">{note.text}</p>
                    {note.from_ground && <span className="text-xs text-blue-400">From Ground</span>}
                  </div>
                ))}
              </div>
              <div className="mt-4 flex gap-2">
                <input
                  type="text"
                  value={replyText}
                  onChange={e => setReplyText(e.target.value)}
                  placeholder="Ground reply..."
                  className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <button
                  onClick={() => handleReply(selectedCase.id)}
                  disabled={loading || !replyText.trim()}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-400 text-gray-900 font-medium rounded-lg disabled:opacity-50"
                >
                  {loading ? 'Sending...' : 'Send Reply'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Sync Queue */}
        <div className="mt-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Sync Queue</h2>
            <div className="flex gap-2">
              <button onClick={fetchSyncQueue} className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded">Refresh</button>
              <button onClick={handleFlush} disabled={syncLoading} className="px-3 py-1 text-sm bg-teal-500 hover:bg-teal-400 text-gray-900 rounded disabled:opacity-50">
                {syncLoading ? 'Flushing...' : 'Flush Queue'}
              </button>
            </div>
          </div>
          {syncQueue.length === 0 ? (
            <p className="text-gray-500 text-center py-4">Queue empty</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {syncQueue.map((item, idx) => (
                <div key={idx} className="p-3 bg-gray-700/50 rounded-lg text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-teal-400">{item.kind}</span>
                    <span className={`px-2 py-0.5 text-xs rounded ${
                      item.status === 'queued' ? 'bg-yellow-500/20 text-yellow-400' :
                      item.status === 'sent' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="text-gray-400 text-xs mt-1">Priority: {item.priority} • {new Date(item.created_at).toLocaleString()}</p>
                  {item.ref_id && <p className="text-xs text-gray-500 mt-1">Ref: {item.ref_id}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}