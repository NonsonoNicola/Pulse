import type {
  User,
  Astronaut,
  CrewSummary,
  Assessment,
  ChatResult,
  Case,
  SBARPacket,
  SyncQueueItem,
  LinkStatus,
  Notification,
  DemoState,
} from '../types';

const API_BASE = '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function login(username: string, password: string) {
  return fetchJson<{ user: User; token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function logout() {
  return fetchJson<{ ok: boolean }>('/auth/logout', { method: 'POST' });
}

export async function updatePreferences(payload: { locale?: string; explanation_level?: string }) {
  return fetchJson<User>('/auth/me/preferences', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function me() {
  return fetchJson<User>('/auth/me');
}

export async function health() {
  return fetchJson<{ status: string; llm: unknown }>('/health');
}

export async function getStatus(astronautId: string, locale = 'en') {
  return fetchJson<Astronaut>(`/astronauts/${astronautId}/status?locale=${locale}`);
}

export async function getTrends(astronautId: string, days = 30, locale = 'en') {
  return fetchJson<unknown>(`/astronauts/${astronautId}/trends?days=${days}&locale=${locale}`);
}

export async function getBooklet(astronautId: string) {
  return fetchJson<{ profile: Astronaut; status: unknown; events: unknown[] }>(`/booklet/${astronautId}`);
}

export async function exportBooklet(astronautId: string) {
  const res = await fetch(`${API_BASE}/booklet/${astronautId}/export`, { credentials: 'include' });
  return res.blob();
}

export async function getCrewSummary(locale = 'en') {
  return fetchJson<CrewSummary>(`/crew/summary?locale=${locale}`);
}

export async function getCrewMembers() {
  return fetchJson<unknown[]>(`/crew/members`);
}

export async function submitCheckin(payload: any) {
  return fetchJson<{ event: unknown }>('/checkin', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function skipCheckin(payload: any) {
  return fetchJson<{ event: unknown }>('/checkin/skip', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getSymptoms(locale = 'en') {
  return fetchJson<{ symptoms: { id: string; label: string; group: string }[] }>(`/checkin/symptoms?locale=${locale}`);
}

export async function chat(payload: any) {
  return fetchJson<ChatResult>('/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function chatStream(
  payload: any,
  onChunk: (chunk: string) => void,
  onDone: (assessment: Assessment) => void
) {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) return;
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'content') {
            onChunk(data.data);
          } else if (data.type === 'done') {
            onDone(data.assessment);
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  }
}

export async function startEmergency(payload: any) {
  return fetchJson<{ case_id: string; sbar_id: string; status: string }>('/emergency/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getCase(caseId: string) {
  return fetchJson<Case>(`/emergency/cases/${caseId}`);
}

export async function getCases() {
  return fetchJson<Case[]>('/emergency/cases');
}

export async function addCaseNote(caseId: string, payload: any) {
  return fetchJson<{ id: string; case_id: string; text: string; priority: number; created_at: string }>(
    `/emergency/cases/${caseId}/notes`,
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export async function getSBARPackets(caseId: string) {
  return fetchJson<{ sbar_packets: SBARPacket[] }>(`/emergency/cases/${caseId}/sbar`);
}

export async function generateSBAR(caseId: string) {
  return fetchJson<{ sbar_id: string; markdown: string }>(`/emergency/cases/${caseId}/sbar`, {
    method: 'POST',
  });
}

export async function getSyncQueue(status?: string, limit = 100) {
  return fetchJson<SyncQueueItem[]>(`/sync/queue${status ? `?status=${status}&limit=${limit}` : `?limit=${limit}`}`);
}

export async function flushSync() {
  return fetchJson<{ flushed: boolean; at: string }>('/sync/flush', { method: 'POST' });
}

export async function getLinkStatus() {
  return fetchJson<LinkStatus>('/sync/link/status');
}

export async function setLinkConfig(rttSeconds: number, mode?: string) {
  return fetchJson<LinkStatus>('/sync/link/config', {
    method: 'POST',
    body: JSON.stringify({ rtt_seconds: rttSeconds, mode }),
  });
}

export async function getNotifications(unreadOnly = false, limit = 50) {
  return fetchJson<Notification[]>(`/notifications?unread_only=${unreadOnly}&limit=${limit}`);
}

export async function markNotificationRead(id: string) {
  return fetchJson<{ ok: boolean }>(`/notifications/${id}/read`, { method: 'POST' });
}

export async function generateNotifications() {
  return fetchJson<{ ok: boolean }>('/notifications/generate', { method: 'POST' });
}

export async function runScenario(scenario: string, action: string) {
  return fetchJson<{ injected: number; scenario: string; action: string }>('/demo/scenario', {
    method: 'POST',
    body: JSON.stringify({ scenario, action }),
  });
}

export async function getDemoState() {
  return fetchJson<DemoState>('/demo/state');
}

export async function resetDemo() {
  return fetchJson<unknown>('/demo/reset', { method: 'POST' });
}

export async function getEvents(astronautId: string, limit = 200) {
  return fetchJson<unknown[]>(`/events?astronaut_id=${astronautId}&limit=${limit}&ascending=false`);
}