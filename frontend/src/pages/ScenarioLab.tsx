import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';

const SCENARIOS = [
  {
    id: 'S1',
    label: 'S1 — Crew CO₂ Drift',
    description: 'CO₂ rises over 3 days. All 4 crew show coordinated HRV↓, sleep↓, symptoms↑. CO₂ alert orange, crew finding 4/4, correlation r=0.96.',
    activeByDefault: true,
  },
  {
    id: 'S2',
    label: 'S2 — Single Infection (Maya)',
    description: 'Inject 4 days of fever, elevated HR, poor sleep for Maya. She goes orange (skin_temp +1.1°C, HR yellow).',
    action: { scenario: 'S2', action: 'inject' },
  },
  {
    id: 'S3',
    label: 'S3 — Blackout + Backfill (Luca)',
    description: 'Luca has 3-day gap (gray, coverage 27%). Backfill restores 3 days of vitals/check-ins. Luca becomes yellow, coverage 93%.',
    action: { scenario: 'S3', action: 'backfill' },
  },
  {
    id: 'S4',
    label: 'S4 — Emergency in Autonomy',
    description: 'Elena reports chest pain. Emergency protocol activates, SBAR queued. Link slider simulates Live → Async → Assisted → Full autonomy.',
    action: { scenario: 'S4', action: 'inject' },
  },
  {
    id: 'S5',
    label: 'S5 — Faulty Sensor + Bias (Aiko)',
    description: 'Aiko SpO₂ sensor fails (discordant with HR/RR). Sensor quality flag yellow, manual SpO₂ recheck suggested. Never goes red from faulty sensor.',
    action: { scenario: 'S5', action: 'recheck' },
  },
];

export function ScenarioLab() {
  const { user } = useAuth();
  const { runScenario, startEmergency } = useApi();
  const [injecting, setInjecting] = useState<string | null>(null);

  if (!user || !['ground', 'admin'].includes(user.role)) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Access restricted to Ground and Admin</p>
      </div>
    );
  }

  const handleInject = async (scenario: { id: string; action: { scenario: string; action: string } }) => {
    setInjecting(scenario.id);
    try {
      if (scenario.id === 'S4') {
        const created = await startEmergency({
          astronaut_id: 'astronaut_01',
          protocol_key: 'chest_pain',
          reason: 'Chest pain radiating to left arm',
          initial_vitals: { resting_hr: 95, spo2: 96 },
        });
        if (!created) throw new Error('Emergency could not be started');
      } else {
        const result = await runScenario(scenario.action.scenario, scenario.action.action);
        if (!result) throw new Error('Injection failed');
      }
      alert(`${scenario.id} injected successfully`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Injection failed');
    } finally {
      setInjecting(null);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Scenario Laboratory</h1>
      <p className="text-gray-400">Inject demo scenarios into the live system. Each click calls the real API.</p>

      <div className="space-y-3">
        {SCENARIOS.map(s => (
          <div
            key={s.id}
            className={`p-4 rounded-lg border transition-colors ${
              s.activeByDefault
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-gray-800/50 border-gray-700 hover:border-teal-500/50'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-bold text-lg">{s.label}</h3>
                <p className="text-gray-400 text-sm mt-1">{s.description}</p>
                {s.activeByDefault && (
                  <span className="inline-block mt-2 px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                    Active by default (seed)
                  </span>
                )}
              </div>
              {s.action && (
                <button
                  onClick={() => handleInject(s)}
                  disabled={injecting === s.id}
                  className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-gray-900 font-medium rounded-lg disabled:opacity-50 whitespace-nowrap"
                >
                  {injecting === s.id ? 'Injecting...' : 'Inject'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <h3 className="font-bold mb-2">Direct Links for Judges</h3>
        <p className="text-sm text-gray-400 mb-3">These deep links inject scenarios via URL parameter:</p>
        <div className="space-y-2 text-sm font-mono">
          <code className="block bg-gray-900 px-3 py-2 rounded">/?demo=S1  → CO₂ drift (default)</code>
          <code className="block bg-gray-900 px-3 py-2 rounded">/?demo=S2  → Maya infection</code>
          <code className="block bg-gray-900 px-3 py-2 rounded">/?demo=S3  → Luca backfill</code>
          <code className="block bg-gray-900 px-3 py-2 rounded">/?demo=S4  → Emergency chest pain</code>
          <code className="block bg-gray-900 px-3 py-2 rounded">/?demo=S5  → Aiko sensor fault</code>
        </div>
      </div>
    </div>
  );
}