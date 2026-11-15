import { useState } from 'react';

interface ProtocolStepperProps {
  steps: string[];
  reassessMinutes?: number;
  onStepComplete?: (index: number) => void;
}

export function ProtocolStepper({ steps, reassessMinutes, onStepComplete }: ProtocolStepperProps) {
  const [completed, setCompleted] = useState<Set<number>>(new Set());
  const [currentStep, setCurrentStep] = useState(0);

  const handleComplete = (index: number) => {
    setCompleted(prev => new Set([...prev, index]));
    if (index === currentStep && currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
    onStepComplete?.(index);
  };

  const handleUndo = (index: number) => {
    setCompleted(prev => {
      const next = new Set(prev);
      next.delete(index);
      return next;
    });
  };

  return (
    <div className="space-y-3" role="list" aria-label="Emergency protocol steps">
      {steps.map((step, index) => {
        const isDone = completed.has(index);
        const isCurrent = index === currentStep && !isDone;
        return (
          <div
            key={index}
            className={`flex items-start gap-3 p-4 rounded-lg border transition-all ${
              isDone
                ? 'bg-green-500/10 border-green-500/30'
                : isCurrent
                ? 'bg-teal-500/10 border-teal-500/30 ring-1 ring-teal-500/20'
                : 'bg-gray-800/50 border-gray-700'
            }`}
            role="listitem"
          >
            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full border-2 text-sm font-mono font-bold">
              {isDone ? (
                <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`font-medium ${isDone ? 'text-green-300 line-through' : 'text-gray-100'}`}>
                {step}
              </p>
              {reassessMinutes && index === steps.length - 1 && (
                <p className="text-xs text-gray-400 mt-1">
                  Reassess in {reassessMinutes} minutes
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isDone ? (
                <button
                  onClick={() => handleUndo(index)}
                  className="px-3 py-1 text-xs text-gray-400 hover:text-gray-200 border border-gray-700 rounded"
                >
                  Undo
                </button>
              ) : (
                <button
                  onClick={() => handleComplete(index)}
                  className="px-4 py-2 text-sm font-medium text-gray-900 bg-teal-400 hover:bg-teal-300 rounded disabled:opacity-50"
                  disabled={index > currentStep}
                >
                  {isCurrent ? 'Done' : 'Wait'}
                </button>
              )}
            </div>
          </div>
        );
      })}
      {completed.size === steps.length && (
        <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
          <p className="text-green-300 font-medium">All steps completed</p>
          {reassessMinutes && (
            <p className="text-xs text-gray-400 mt-1">Next reassessment in {reassessMinutes} minutes</p>
          )}
        </div>
      )}
    </div>
  );
}