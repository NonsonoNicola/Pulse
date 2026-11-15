export type Level = 'green' | 'yellow' | 'orange' | 'red' | 'gray';
export type Confidence = 'low' | 'medium' | 'high';
export type Role = 'astronaut' | 'cmo' | 'ground' | 'admin';

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  astronaut_id: string | null;
  locale: string;
  explanation_level: string;
}

export interface Astronaut {
  id: string;
  name: string;
  role_title: string;
  color: string;
  level: Level;
  confidence: Confidence;
  coverage: number;
  primary_reason: string;
  reasons: Reason[];
  data_quality: DataQualityFlag[];
  environmental_alerts: EnvironmentalAlert[];
  deviations: Deviation[];
  hypotheses: Hypothesis[];
  tests: Test[];
  gamification: GamificationState;
  baselines: Record<string, Baseline>;
  computed_at?: string;
  backfilled_recent?: string[];
}

export interface Baseline {
  center: number;
  spread: number;
  origin: string;
  n_obs: number;
  frozen: boolean;
}

export interface Reason {
  rule_id: string;
  level: Level;
  scope: string;
  kind: string;
  metric: string | null;
  value: number | null;
  threshold: number | null;
  days: number;
  explanation: string;
  protocol: string | null;
  card_id: string | null;
  value_text: string;
  quality: string;
  evidence: Evidence[];
}

export interface Evidence {
  event_id: string;
  type: string;
  at: string;
}

export interface DataQualityFlag {
  date: string;
  type: string;
  quality: string;
  reason: string;
}

export interface EnvironmentalAlert {
  rule_id: string;
  level: Level;
  scope: string;
  metric: string;
  value: number;
  threshold: number;
  days: number;
  explanation: string;
  protocol: string | null;
  card_id: string | null;
  value_text: string;
  threshold_text: string;
}

export interface Deviation {
  metric: string;
  direction: 'above' | 'below';
  z: number;
  recent: number;
  baseline_center: number;
  baseline_spread: number;
  magnitude: number;
  percent: number | null;
  n: number;
  quality: string;
  coverage: number;
  baseline_origin: string;
}

export interface Hypothesis {
  id: string;
  title: string;
  card_id: string;
  score: number;
  coverage: number;
  support: string[];
  against: string[];
  observed: string[];
}

export interface Test {
  id: string;
  astronaut_id: string;
  date: string;
  test: string;
  why_en: string;
  why_it: string;
  minutes: number;
  status: 'suggested' | 'completed';
  completed_at: string | null;
  created_at: string;
}

export interface GamificationState {
  honesty_days: number;
  honesty_days_last_30: number;
  honesty_note_en: string;
  honesty_note_it: string;
  time_saved_minutes_7d: number;
  time_saved_note_en: string;
  time_saved_note_it: string;
  daily_ring: {
    checkin: boolean;
    test: boolean;
  };
  test_today: string | null;
  sentinel: SentinelBadge | null;
  crew_goal: CrewGoal;
  enabled: boolean;
  disabled_reason: string | null;
  no_leaderboard: boolean;
}

export interface SentinelBadge {
  awarded: boolean;
  lead_days: number;
  symptom_event_id: string;
  alert_event_id: string;
  text_en: string;
  text_it: string;
}

export interface CrewGoal {
  label_en: string;
  label_it: string;
  value: number;
  target: number;
  reached: boolean;
}

export interface CrewSummary {
  level_counts: Record<Level, number>;
  member_count: number;
  coverage: number;
  findings: CrewFinding[];
  environmental_alerts: EnvironmentalAlert[];
  crew_goal: CrewGoal | null;
  computed_at: string;
  note_en: string;
  note_it: string;
}

export interface CrewFinding {
  id: string;
  window_start: string;
  window_end: string;
  metrics: CrewFindingMetric[];
  direction: string;
  members: CrewFindingMember[];
  member_count: number;
  env_correlations: EnvCorrelation[];
  confidence: Confidence;
  status: string;
  description_en: string;
  description_it: string;
  coverage: number;
  not_causation: boolean;
}

export interface CrewFindingMetric {
  metric: string;
  direction: 'above' | 'below';
  mean_z: number;
  members: number;
}

export interface CrewFindingMember {
  astronaut_id: string;
  z_by_metric: Record<string, number>;
}

export interface EnvCorrelation {
  env_metric: string;
  r: number;
  p_value: number;
  lag_days: number;
  n: number;
  confidence: Confidence;
  significant: boolean;
  note: string;
}

export interface Assessment {
  triage_level: Level;
  rule_level: Level;
  summary_simple: string;
  observations: Observation[];
  hypotheses: HypothesisOut[];
  confidence: Confidence;
  confidence_reasons: string[];
  do_now: string[];
  outside_protocol: boolean;
  reassess_in_minutes: number | null;
  escalate_when: string[];
  suggested_tests: SuggestedTest[];
  questions_for_user: string[];
  questions_for_ground: string[];
  needs_cmo_confirmation: CmoAction[];
  sources: string[];
  disclaimer_key: string;
  warnings: string[];
}

export interface Observation {
  metric: string;
  finding: string;
  evidence_event_ids: string[];
}

export interface HypothesisOut {
  name: string;
  support: string[];
  against: string[];
  card_ids: string[];
}

export interface SuggestedTest {
  test: string;
  why: string;
  minutes: number;
}

export interface CmoAction {
  action: string;
  reason: string;
}

export interface ChatResult {
  assessment: Assessment;
  markdown: string;
  mode: string;
  model: string | null;
  emergency: boolean;
  case_id: string | null;
}

export interface Case {
  id: string;
  astronaut_id: string;
  level: Level;
  status: string;
  title: string;
  protocol_id: string | null;
  opened_at: string;
  updated_at: string;
  notes: CaseNote[];
  sbar_ids: string[];
}

export interface CaseNote {
  id: string;
  text: string;
  author_id: string;
  priority: number;
  at: string;
  from_ground?: boolean;
}

export interface SBARPacket {
  id: string;
  case_id: string;
  astronaut_id: string;
  priority: number;
  payload: SBARPayload;
  markdown: string;
  created_at: string;
}

export interface SBARPayload {
  case_id: string;
  astronaut_id: string;
  situation: string;
  background: Record<string, unknown>;
  assessment: string;
  recommendation: string;
}

export interface SyncQueueItem {
  id: string;
  kind: string;
  ref_id: string | null;
  priority: number;
  payload: string;
  status: 'queued' | 'sent' | 'acked';
  attempts: number;
  next_attempt_at: string | null;
  created_at: string;
  sent_at: string | null;
  acked_at: string | null;
}

export interface Notification {
  id: string;
  user_id: string | null;
  astronaut_id: string | null;
  level: Level;
  kind: string;
  title: string;
  body: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
  quiet_suppressed: number;
}

export interface LinkStatus {
  mode: 'live' | 'async' | 'assisted' | 'full';
  rtt_seconds: number;
  last_contact: string | null;
  autonomy_mode: string;
  description: string;
}

export interface DemoState {
  seeded_at: string;
  mission_id: string;
  scenarios: Record<string, DemoScenario>;
}

export interface DemoScenario {
  active: boolean;
  label: string;
  state?: string;
}