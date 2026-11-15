interface EvidenceChipProps {
  cardId: string;
  onClick?: () => void;
}

export function EvidenceChip({ cardId, onClick }: EvidenceChipProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center px-2 py-1 text-xs font-mono bg-gray-800 rounded border border-gray-700 hover:border-teal-500 hover:text-teal-400 transition-colors"
      title={`Knowledge card: ${cardId}`}
    >
      <span className="text-teal-400">📄</span>
      <span className="ml-1">{cardId}</span>
    </button>
  );
}