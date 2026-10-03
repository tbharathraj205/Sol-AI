import { Cpu, ShieldCheck, AlertCircle, GitBranch } from "lucide-react";

export default function MorphologyCard({ morphology, query = "" }) {
  if (!morphology) {
    return (
      <div className="bg-[#0B132B]/90 border border-[#C9A227]/30 rounded-2xl p-6 shadow-xl backdrop-blur-md text-slate-300">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[#E5C158] mb-2 flex items-center space-x-2">
          <GitBranch className="w-4 h-4 text-[#C9A227]" />
          <span>Morphology</span>
        </h3>
        <p className="text-sm italic text-slate-400">Morphological analysis unavailable.</p>
      </div>
    );
  }

  const pos = morphology.pos || "Unknown";
  const analysisType = (morphology.analysis_type || "core").toLowerCase();
  const rawMorph = morphology.raw_morphology || "";
  const isCore = analysisType === "core";

  // Consume structured Case, Number, and Segments directly from backend
  const parsedCase = morphology.case || "-";
  const parsedNumber = morphology.number || "-";
  const segments = (morphology.segments && morphology.segments.length > 0)
    ? morphology.segments
    : (rawMorph ? [{ tamil: query, latin: "", role: rawMorph.replace(/\+/g, " + ") }] : []);

  return (
    <div className="h-full flex flex-col bg-[#0A0A0A]/90 border border-white/5 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-5">
      {/* Title Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-3">
        <h3 className="text-lg font-serif text-[#F7F3EA] flex items-center space-x-2">
          <GitBranch className="w-5 h-5 text-[#C9A227]" />
          <span>Morphology</span>
        </h3>

        {/* Provenance FST Badge */}
        <div
          className={`flex items-center space-x-1.5 text-xs font-medium px-2.5 py-0.5 rounded-full border ${
            isCore
              ? "bg-[#C9A227]/5 text-emerald-400 border-emerald-500/30"
              : "bg-[#C9A227]/5 text-[#E5C158] border-[#C9A227]/30"
          }`}
        >
          {isCore ? (
            <>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Core FST</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-3.5 h-3.5 text-[#E5C158]" />
              <span>Guesser FST</span>
            </>
          )}
        </div>
      </div>

      {/* Segmented Morphological Pill Chain */}
      {rawMorph ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Morpheme Breakdown:
          </div>
          <div className="flex flex-wrap items-center gap-2 p-3.5 rounded-xl bg-[#121212]/90 border border-white/5">
          {segments.map((seg, idx) => (
            <div key={idx} className="flex items-center space-x-2">
              <div className="flex flex-col items-center px-3 py-2 rounded-lg bg-[#18181B] border border-white/10 min-w-[70px] text-center">
                <span className="text-sm font-bold text-[#F7F3EA] font-serif-tamil">
                  {seg.tamil}
                </span>
                <span className="text-[10px] text-slate-400 font-sans italic">
                  {seg.latin}
                </span>
                <span className="text-[9px] text-slate-300 font-mono mt-0.5">
                  {seg.role}
                </span>
              </div>
              {idx < segments.length - 1 && (
                <span className="text-slate-500 font-bold text-base">+</span>
              )}
            </div>
          ))}
        </div>
      </div>
      ) : (
        <div className="flex items-center space-x-2 p-3.5 rounded-xl bg-[#121212]/90 border border-white/5 text-slate-400 text-sm italic">
          <AlertCircle className="w-4 h-4 text-amber-500/70" />
          <span>No precise morpheme segmentation available for this root form.</span>
        </div>
      )}

      {/* Metadata Key-Value Table */}
      <div className="grid grid-cols-2 gap-3 text-xs mt-auto">
        <div className="p-3 rounded-xl bg-[#121212]/60 border border-white/5 space-y-1">
          <div className="text-[10px] font-bold uppercase text-slate-500">Full form:</div>
          <div className="text-sm font-medium text-[#F7F3EA] font-serif-tamil">{query}</div>
        </div>
        <div className="p-3 rounded-xl bg-[#121212]/60 border border-white/5 space-y-1">
          <div className="text-[10px] font-bold uppercase text-slate-500">Type:</div>
          <div className="text-sm font-medium text-[#F7F3EA]">
            {pos}{pos !== "Unknown" ? " (inflected)" : ""}
          </div>
        </div>
        <div className="p-3 rounded-xl bg-[#121212]/60 border border-white/5 space-y-1">
          <div className="text-[10px] font-bold uppercase text-slate-500">Case:</div>
          <div className="text-sm font-medium text-slate-300">{parsedCase}</div>
        </div>
        <div className="p-3 rounded-xl bg-[#121212]/60 border border-white/5 space-y-1">
          <div className="text-[10px] font-bold uppercase text-slate-500">Number:</div>
          <div className="text-sm font-medium text-slate-300">{parsedNumber}</div>
        </div>
      </div>
    </div>
  );
}
