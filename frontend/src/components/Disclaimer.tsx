export function Disclaimer({ locale = 'en' }: { locale?: string }) {
  const texts = {
    en: {
      clinical: 'Research prototype — not a medical device. These are suggestions, not a diagnosis. A CMO or flight surgeon decides on treatment.',
      draft: 'Clinical content is a draft and needs review by a flight-medicine physician.',
    },
    it: {
      clinical: 'Prototipo di ricerca — non è un dispositivo medico. Questi sono suggerimenti, non una diagnosi. Le decisioni terapeutiche spettano al CMO o al flight surgeon.',
      draft: 'Il contenuto clinico è una bozza e richiede la revisione di un medico di medicina spaziale.',
    },
  };

  const t = texts[locale as keyof typeof texts] || texts.en;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 px-4 py-2 bg-gray-950/95 backdrop-blur border-t border-gray-800">
      <div className="max-w-7xl mx-auto flex flex-col gap-1 text-center text-xs text-gray-500">
        <p>{t.clinical}</p>
        <p>{t.draft}</p>
      </div>
    </div>
  );
}