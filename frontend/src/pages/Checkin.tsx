import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

const SCALES = [
  { id: 'mood', label: 'Mood', emoji: '😐' },
  { id: 'energy', label: 'Energy', emoji: '⚡' },
  { id: 'sleep_quality', label: 'Sleep Quality', emoji: '😴' },
  { id: 'hydration', label: 'Hydration', emoji: '💧' },
  { id: 'appetite', label: 'Appetite', emoji: '🍽️' },
];

const SKIP_REASONS = [
  { value: 'blackout', label: 'Comms blackout' },
  { value: 'sensor_issue', label: 'Sensor issue' },
  { value: 'no_time', label: 'No time' },
  { value: 'other', label: 'Other' },
];

export function Checkin() {
  const { submitCheckin, skipCheckin, getSymptoms } = useApi();
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [symptoms, setSymptoms] = useState<{ id: string; label: string; group: string }[]>([]);

  const [form, setForm] = useState<{
    mood: number;
    energy: number;
    sleep_quality: number;
    sleep_hours: number;
    symptoms: string[];
    pain_site: string;
    pain_intensity: number;
    hydration: number;
    appetite: number;
    note: string;
    skip_reason: string;
  }>({
    mood: 3,
    energy: 3,
    sleep_quality: 3,
    sleep_hours: 7,
    symptoms: [],
    pain_site: '',
    pain_intensity: 0,
    hydration: 3,
    appetite: 3,
    note: '',
    skip_reason: 'no_time',
  });

  const steps = [
    { id: 'scales', label: 'How you feel' },
    { id: 'sleep', label: 'Sleep' },
    { id: 'symptoms', label: 'Symptoms' },
    { id: 'pain', label: 'Pain' },
    { id: 'note', label: 'Note' },
  ];

  useEffect(() => {
    getSymptoms().then(data => {
      if (data) setSymptoms(data.symptoms);
    });
  }, [getSymptoms]);

  const handleScaleChange = (id: string, value: number) => {
    setForm(prev => ({ ...prev, [id]: value }));
  };

  const handleSymptomToggle = (id: string) => {
    setForm(prev => ({
      ...prev,
      symptoms: prev.symptoms.includes(id)
        ? prev.symptoms.filter(s => s !== id)
        : [...prev.symptoms, id],
    }));
  };

  const handleNext = () => {
    if (step < steps.length - 1) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleSubmit = async (skip = false) => {
    setLoading(true);
    try {
      if (skip) {
        await skipCheckin({ reason: form.skip_reason, note: form.note });
      } else {
        const payload = {
          mood: form.mood,
          energy: form.energy,
          sleep_quality: form.sleep_quality,
          sleep_hours: form.sleep_hours,
          symptoms: form.symptoms,
          pain: form.pain_site ? { site: form.pain_site, intensity: form.pain_intensity } : null,
          hydration: form.hydration,
          appetite: form.appetite,
          note: form.note,
        };
        await submitCheckin(payload);
      }
      navigate('/');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Check-in failed');
    } finally {
      setLoading(false);
    }
  };

  const currentStep = steps[step];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Progress */}
      <div className="flex items-center gap-2">
        {steps.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                i < step ? 'bg-teal-500 text-gray-900' : i === step ? 'bg-teal-500/20 text-teal-400 ring-2 ring-teal-500' : 'bg-gray-700 text-gray-500'
              }`}
            >
              {i + 1}
            </div>
            {i < steps.length - 1 && <div className="w-12 h-0.5 bg-gray-700 ml-1" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-6">
        <h2 className="text-xl font-bold">{currentStep.label}</h2>

        {step === 0 && (
          <div className="space-y-6">
            {SCALES.map(scale => (
              <div key={scale.id} className="space-y-2">
                <label className="block text-sm font-medium text-gray-300 flex items-center gap-2">
                  <span className="text-2xl">{scale.emoji}</span>
                  {scale.label}
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(v => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => handleScaleChange(scale.id, v)}
                      className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                        (form as unknown as Record<string, number>)[scale.id] === v
                          ? 'bg-teal-500 text-gray-900 shadow-lg shadow-teal-500/25'
                          : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Sleep duration (hours)</label>
              <input
                type="number"
                step="0.5"
                min="0"
                max="16"
                value={form.sleep_hours}
                onChange={e => setForm(prev => ({ ...prev, sleep_hours: parseFloat(e.target.value) || 0 }))}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Sleep quality</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map(v => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleScaleChange('sleep_quality', v)}
                    className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                      form.sleep_quality === v
                        ? 'bg-teal-500 text-gray-900'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">Tap to toggle. No symptom is pre-selected.</p>
            <div className="flex flex-wrap gap-2">
              {symptoms.map(s => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleSymptomToggle(s.id)}
                  className={`px-3 py-2 rounded-lg text-sm transition-all ${
                    form.symptoms.includes(s.id)
                      ? 'bg-red-500/20 border border-red-500/30 text-red-300'
                      : 'bg-gray-800 border border-gray-700 text-gray-300 hover:border-teal-500/50'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="p-3 bg-gray-800/50 rounded-lg text-xs text-gray-400">
              "I don't know" and "Prefer to say it by voice" are always valid choices.
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Pain site</label>
              <input
                type="text"
                value={form.pain_site}
                onChange={e => setForm(prev => ({ ...prev, pain_site: e.target.value }))}
                placeholder="e.g., lower back, right shoulder"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Intensity (0-10)</label>
              <div className="flex gap-2">
                {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(v => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setForm(prev => ({ ...prev, pain_intensity: v }))}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                      form.pain_intensity === v
                        ? 'bg-teal-500 text-gray-900'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">Note (optional)</label>
              <textarea
                value={form.note}
                onChange={e => setForm(prev => ({ ...prev, note: e.target.value }))}
                rows={3}
                placeholder="Anything else? Voice input available..."
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>
        )}

        {/* Skip option always available */}
        <div className="pt-4 border-t border-gray-700">
          <button
            type="button"
            onClick={() => {
              setForm(prev => ({ ...prev, skip_reason: 'no_time' }));
              handleSubmit(true);
            }}
            className="w-full py-3 text-gray-400 hover:text-gray-200 border border-gray-700 rounded-lg transition-colors"
          >
            Skip today — {SKIP_REASONS.find(r => r.value === form.skip_reason)?.label || 'No time'}
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex gap-3">
        {step > 0 && (
          <button
            onClick={handleBack}
            disabled={loading}
            className="flex-1 py-3 px-4 text-gray-300 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            Back
          </button>
        )}
        {step < steps.length - 1 ? (
          <button
            onClick={handleNext}
            disabled={loading}
            className="flex-1 py-3 px-4 bg-teal-500 text-gray-900 font-medium rounded-lg hover:bg-teal-400 disabled:opacity-50"
          >
            Next
          </button>
        ) : (
          <button
            onClick={() => handleSubmit(false)}
            disabled={loading}
            className="flex-1 py-3 px-4 bg-teal-500 text-gray-900 font-medium rounded-lg hover:bg-teal-400 disabled:opacity-50"
          >
            {loading ? 'Submitting...' : 'Submit Check-in'}
          </button>
        )}
      </div>
    </div>
  );
}