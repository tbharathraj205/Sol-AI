import { BookOpen, Info } from "lucide-react";

export default function MeaningCard({ senses: propSenses, meaning, englishMeaning, query }) {
  let displaySenses = [];

  if (propSenses && Array.isArray(propSenses) && propSenses.length > 0) {
    displaySenses = propSenses.slice(0, 2).map((s) => ({
      title: s.title || s.raw_text,
      description: s.english_translation || s.description || "",
    }));
  } else if (meaning) {
    // Graceful backward-compatible fallback if structured senses are not provided
    const rawSenses = meaning
      .split(/;/)
      .map((s) => s.trim())
      .filter(Boolean);

    const englishSenses = englishMeaning
      ? englishMeaning.split(/;/).map((s) => s.trim()).filter(Boolean)
      : [];

    displaySenses = rawSenses.slice(0, 2).map((sense, idx) => {
      const parts = sense.split(/—|-|:/);
      const title = parts[0]?.trim();
      const desc = parts.slice(1).join(" ").trim();
      return {
        title: title || sense,
        description: englishSenses[idx] || desc || "",
      };
    });
  }

  if (displaySenses.length === 0) {
    return (
      <div className="bg-[#0B132B]/90 border border-[#C9A227]/30 rounded-2xl p-6 shadow-xl backdrop-blur-md text-slate-300">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[#E5C158] mb-2 flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-[#C9A227]" />
          <span>Meaning</span>
        </h3>
        <p className="text-sm italic text-slate-400">Meaning not established from the available evidence.</p>
      </div>
    );
  }

  return (
    <div className="h-full bg-[#0A0A0A]/90 border border-white/5 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-5">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-3">
        <h3 className="text-lg font-serif text-[#F7F3EA] flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-[#C9A227]" />
          <span>Meaning</span>
        </h3>
        <span className="text-xs text-slate-500 font-sans font-medium">
          {displaySenses.length} Senses Preserved
        </span>
      </div>

      {/* Numbered Definitions List */}
      <div className="space-y-4">
        {displaySenses.map((sense, idx) => (
          <div
            key={idx}
            className="flex items-start space-x-3 text-[#F7F3EA]"
          >
            <div className="font-serif text-lg font-medium pt-0.5 shrink-0">
              {idx + 1}.
            </div>
            <div className="flex-1 space-y-1 pt-1">
              <div className="text-[15px] font-semibold text-[#F7F3EA] font-sans">
                {sense.title}
              </div>
              {sense.description && (
                <div className="text-[13px] text-slate-400 font-sans leading-relaxed">
                  {sense.description}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Gold Context Callout Box */}
      <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-[#C9A227]/5 border border-[#C9A227]/20 text-xs text-slate-400 leading-relaxed mt-2">
        <Info className="w-4 h-4 shrink-0 text-[#C9A227] mt-0.5" />
        <p>
          <span className="text-[#E5C158] font-medium block">The meaning may vary based on context.</span>
          See literary evidence for usage.
        </p>
      </div>
    </div>
  );
}
