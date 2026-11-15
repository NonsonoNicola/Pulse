import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from './useAuth';

const DEMO_ACTIONS: Record<string, { scenario: string; action: string }> = {
  S1: { scenario: 'S1', action: 'inject' }, // already active after seed
  S2: { scenario: 'S2', action: 'inject' },
  S3: { scenario: 'S3', action: 'backfill' },
  S4: { scenario: 'S4', action: 'inject' }, // emergency case
  S5: { scenario: 'S5', action: 'recheck' },
};

async function postJson(path: string, body: unknown): Promise<Response> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `HTTP ${res.status}`);
  }
  return res;
}

export function useDemo() {
  const { user, loading } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [injecting, setInjecting] = useState<string | null>(null);

  useEffect(() => {
    const demo = searchParams.get('demo');
    if (!demo || !DEMO_ACTIONS[demo]) return;

    // Keep ?demo through the login screen: it is consumed only once a session
    // exists, otherwise the injection would run unauthenticated and be lost.
    if (loading || !user) return;

    // Remove the parameter immediately so refreshes and re-renders do not
    // replay the injection.
    setSearchParams({}, { replace: true });

    if (demo === 'S1') return; // S1 is already active in the seeded data

    let cancelled = false;
    const run = async () => {
      setInjecting(demo);
      try {
        if (demo === 'S4') {
          await postJson('/api/emergency/start', {
            astronaut_id: 'astronaut_01',
            protocol_key: 'chest_pain',
            reason: 'Chest pain radiating to left arm',
            initial_vitals: { resting_hr: 95, spo2: 96 },
          });
          if (!cancelled) {
            navigate(user.role === 'astronaut' || user.role === 'cmo' ? '/emergency' : '/ground');
          }
        } else {
          const action = DEMO_ACTIONS[demo];
          await postJson('/api/demo/scenario', action);
          if (!cancelled) {
            if (user.role === 'astronaut') {
              navigate(demo === 'S3' ? '/recover' : '/');
            } else {
              navigate('/crew');
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          window.alert(
            `Could not inject ${demo}: ${err instanceof Error ? err.message : 'unknown error'}. ` +
            'Check that the backend is running, then reload the page.'
          );
        }
      } finally {
        if (!cancelled) setInjecting(null);
      }
    };
    void run();

    return () => {
      cancelled = true;
    };
  }, [searchParams, setSearchParams, navigate, user, loading]);

  return { injecting };
}
