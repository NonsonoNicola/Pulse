import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { ProtocolStepper, SyncStatus } from '../components';
import { TrafficLight, StatusBadge } from '../components';
import type { Astronaut, Case, LinkStatus } from '../types';

const EMERGENCY_PROTOCOLS: Record<string, { title: string; steps: string[]; reassessMinutes: number }> = {
  chest_pain: {
    title: 'Chest Pain — Emergency Protocol',
    steps: [
      'Sit upright, stop activity, and loosen tight clothing.',
      'Repeat oxygen saturation with a second device and check probe placement.',
      'Call the CMO and report both readings, breathing rate, and how the person looks.',
      'Check cabin oxygen, CO₂, and scrubber. Move away from smoke or contaminants.',
      'Prepare oxygen. Use only as directed by the CMO or protocol.',
      'Generate an SBAR packet with both sensor readings and environmental data.',
      'Reassess breathing and oxygen every 5 minutes until stable.',
    ],
    reassessMinutes: 5,
  },
  low_oxygen: {
    title: 'Low Oxygen / Breathing Difficulty',
    steps: [
      'Sit upright, stop activity, and loosen tight clothing.',
      'Repeat oxygen saturation with a second device and check probe placement.',
      'Call the CMO and report both readings, breathing rate, and how the person looks.',
      'Check cabin oxygen, CO₂, and scrubber. Move away from smoke or contaminants.',
      'Prepare oxygen. Use only as directed by the CMO or protocol.',
      'Generate an SBAR packet with both sensor readings and environmental data.',
      'Reassess breathing and oxygen every 5 minutes until stable.',
    ],
    reassessMinutes: 5,
  },
  fever: {
    title: 'Fever / Elevated Temperature',
    steps: [
      'Measure oral temperature and confirm fever.',
      'Hydrate: 500ml water over 30 minutes.',
      'Remove excess clothing, apply cool compress to neck/axilla.',
      'Monitor heart rate, respiratory rate, and SpO₂ every 30 minutes.',
      'If temp > 39°C or worsening: call CMO, consider antipyretic per protocol.',
      'Generate SBAR with vitals and trend data.',
    ],
    reassessMinutes: 60,
  },
  co2_mitigation: {
    title: 'Elevated Cabin CO₂',
    steps: [
      'Verify CO₂ reading with a second sensor and check scrubber status.',
      'Increase ventilation and airflow. Reduce strenuous activity.',
      'Move the crew to the best-ventilated module if CO₂ remains high.',
      'Tell the CMO and record the crew symptom pattern and environmental readings.',
      'Recheck CO₂ and symptoms in 4 hours.',
    ],
    reassessMinutes: 240,
  },
};

export function Emergency() {
  const { user } = useAuth();
  const { startEmergency, getStatus, getCase, getCases, getSBARPackets, generateSBAR, getLinkStatus, setLinkConfig, getCrewMembers } = useApi();

  const [astronautId, setAstronautId] = useState<string>('');
  const [astronaut, setAstronaut] = useState<Astronaut | null>(null);
  const [protocol, setProtocol] = useState<keyof typeof EMERGENCY_PROTOCOLS>('chest_pain');
  const [reason, setReason] = useState('Chest pain radiating to left arm');
  const [activeCase, setActiveCase] = useState<Case | null>(null);
  const [sbarMarkdown, setSbarMarkdown] = useState<string>('');
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [loading, setLoading] = useState(false);
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
    if (astronautId) {
      getStatus(astronautId).then(setAstronaut);
    }
  }, [astronautId, getStatus]);

  useEffect(() => {
    if (!astronautId) return;
    let cancelled = false;
    getCases().then(cases => {
      if (cancelled || !cases) return;
      const open = cases.find(c => c.astronaut_id === astronautId && c.status === 'open');
      if (open) {
        setActiveCase(open);
        if (open.protocol_id && EMERGENCY_PROTOCOLS[open.protocol_id]) {
          setProtocol(open.protocol_id as keyof typeof EMERGENCY_PROTOCOLS);
        }
        getSBARPackets(open.id).then(packets => {
          if (cancelled) return;
          const withMarkdown = packets?.sbar_packets.find(packet => packet.markdown);
          if (withMarkdown) setSbarMarkdown(withMarkdown.markdown);
        });
      } else {
        setActiveCase(prev => (prev && prev.astronaut_id !== astronautId ? null : prev));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [astronautId, getCases, getSBARPackets]);

  useEffect(() => {
    if (!user) return;
    getLinkStatus().then(setLinkStatus);
  }, [getLinkStatus, user]);

  const handleLinkChange = async (rtt: number) => {
    const updated = await setLinkConfig(rtt);
    if (updated) {
      setLinkStatus(updated);
    } else {
      alert('Link configuration requires the ground or admin role.');
    }
  };

  const handleStart = async () => {
    if (!astronautId) return;
    setLoading(true);
    try {
      const result = await startEmergency({
        astronaut_id: astronautId,
        protocol_key: protocol,
        reason,
        initial_vitals: astronaut ? {
          resting_hr: astronaut.reasons.find(r => r.metric === 'resting_hr')?.value,
          spo2: astronaut.reasons.find(r => r.metric === 'spo2')?.value,
        } : undefined,
      });
      if (!result) throw new Error('Emergency could not be started');
      const caseData = await getCase(result.case_id);
      setActiveCase(caseData);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start emergency');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSBAR = async () => {
    if (!activeCase) return;
    setLoading(true);
    try {
      const result = await generateSBAR(activeCase.id);
      if (!result) throw new Error('SBAR could not be generated');
      setSbarMarkdown(result.markdown);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate SBAR');
    } finally {
      setLoading(false);
    }
  };

  const proto = EMERGENCY_PROTOCOLS[protocol];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-red-400">Emergency Protocol</h1>
          <p className="text-gray-400">{proto.title}</p>
        </div>
        {!activeCase && (
          <SyncStatus
            status={linkStatus}
            onConfigChange={user && ['ground', 'admin'].includes(user.role) ? handleLinkChange : undefined}
          />
        )}
      </div>

      {/* Setup */}
      {!activeCase && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
          <h2 className="text-xl font-bold">Activate Emergency Protocol</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Astronaut</label>
              <select
                value={astronautId}
                onChange={e => setAstronautId(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                required
              >
                <option value="">Select astronaut</option>
                {user?.role === 'astronaut' && user.astronaut_id && (
                  <option value={user.astronaut_id}>{user.display_name}</option>
                )}
                {crew.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Protocol</label>
              <select
                value={protocol}
                onChange={e => setProtocol(e.target.value as keyof typeof EMERGENCY_PROTOCOLS)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                {Object.entries(EMERGENCY_PROTOCOLS).map(([key, val]) => (
                  <option key={key} value={key}>{val.title}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Reason / Situation</label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              placeholder="e.g., Chest pain radiating to left arm, started 10 min ago"
            />
          </div>
          <button
            onClick={handleStart}
            disabled={loading || !astronautId}
            className="w-full py-3 bg-red-500 hover:bg-red-400 text-gray-900 font-medium rounded-lg disabled:opacity-50"
          >
            {loading ? 'Activating...' : 'ACTIVATE EMERGENCY PROTOCOL'}
          </button>
        </div>
      )}

      {/* Active Protocol */}
      {activeCase && (
        <div className="space-y-6">
          {/* Case Header */}
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-red-300">{proto.title}</h2>
                <p className="text-gray-400">Case: {activeCase.id}</p>
                <p className="text-sm text-gray-500">Opened: {new Date(activeCase.opened_at).toLocaleString()}</p>
              </div>
              <div className="flex items-center gap-4">
                {astronaut ? (
                  <>
                    <TrafficLight level={astronaut.level} size="sm" showLabel={false} />
                    <StatusBadge level={astronaut.level} compact />
                  </>
                ) : null}
                <button
                  onClick={() => {
                    setActiveCase(null);
                    setSbarMarkdown('');
                  }}
                  className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg"
                >
                  Start another case
                </button>
              </div>
            </div>
          </div>

          {/* Protocol Stepper */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-bold mb-4">Protocol Steps</h3>
            <ProtocolStepper
              steps={proto.steps}
              reassessMinutes={proto.reassessMinutes}
            />
          </div>

          {/* SBAR */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold">SBAR Packet</h3>
              <button
                onClick={handleGenerateSBAR}
                disabled={loading || !!sbarMarkdown}
                className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-gray-900 font-medium rounded-lg disabled:opacity-50"
              >
                {sbarMarkdown ? 'SBAR Generated' : loading ? 'Generating...' : 'Generate SBAR'}
              </button>
            </div>
            {sbarMarkdown && (
              <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-sm whitespace-pre-wrap text-gray-300">
                {sbarMarkdown}
              </div>
            )}
          </div>

          {/* Link status (read-only for astronauts; editable for ground/admin) */}
          <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-2">
            <h3 className="text-lg font-bold">Ground Link Status</h3>
            <SyncStatus
              status={linkStatus}
              inline
              onConfigChange={user && ['ground', 'admin'].includes(user.role) ? handleLinkChange : undefined}
            />
            <p className="text-sm text-gray-400">
              The protocol continues autonomously while the link is degraded.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}