import { useState } from "react";
import WordHeader from "./WordHeader";
import MeaningCard from "./MeaningCard";
import MorphologyCard from "./MorphologyCard";
import LiteraryContextCard from "./LiteraryContextCard";
import RelatedWordsCard from "./RelatedWordsCard";
import AlsoExploreCard from "./AlsoExploreCard";
import InterpretationCard from "./InterpretationCard";
import UncertaintyCard from "./UncertaintyCard";
import EvidencePanel from "./EvidencePanel";
import { ArrowLeft } from "lucide-react";

export default function WordExplorer({ data, onBack = null }) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!data) return null;

  return (
    <div className="relative z-10 mx-auto w-full max-w-[1540px] px-4 sm:px-6 lg:px-8 xl:px-10 pt-5 pb-10">

      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-[#aab6c8] hover:text-[#e5c158] transition-colors mb-4 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to List
        </button>
      )}

      <div className="space-y-6 animate-fade-in relative z-10">
        <WordHeader
          data={data}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        {activeTab === "overview" && (
          <div className="space-y-6">
            {data.query !== data.lemma && data.lemma && (
              <div className="bg-[#C9A227]/10 border border-[#C9A227]/30 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
                <div className="text-slate-300 text-sm">
                  <span className="text-[#E5C158] font-bold">Note:</span>{" "}
                  Showing available details for the inflected word{" "}
                  <span className="font-serif-tamil font-bold text-[#F7F3EA]">
                    "{data.query}"
                  </span>. A direct dictionary meaning might not be available.
                </div>
                <a
                  href={`/?q=${encodeURIComponent(data.lemma)}`}
                  className="px-4 py-2.5 bg-[#C9A227] hover:bg-[#E5C158] text-[#0B132B] text-sm font-bold rounded-xl transition whitespace-nowrap shadow-sm flex items-center justify-center cursor-pointer w-full sm:w-auto"
                >
                  Look for root word "{data.lemma}"
                </a>
              </div>
            )}

            <div className="flex flex-col space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                <div>
                  <MeaningCard
                    senses={data.senses}
                    meaning={data.meaning}
                    englishMeaning={data.english_meaning}
                    query={data.query}
                  />
                </div>
                <div>
                  <MorphologyCard
                    morphology={data.morphology}
                    query={data.query}
                  />
                </div>
              </div>

              <LiteraryContextCard
                contexts={data.literary_context}
                query={data.query}
                lemma={data.lemma}
              />

              {data.uncertainties && data.uncertainties.length > 0 && (
                <UncertaintyCard
                  uncertainties={data.uncertainties}
                  conflicts={data.conflicts}
                />
              )}

              <EvidencePanel
                sources={data.sources}
                summary={data.evidence_summary}
              />
            </div>
          </div>
        )}

        {activeTab === "meanings" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <MeaningCard senses={data.senses} meaning={data.meaning} query={data.query} />
            {data.contextual_interpretation && (
              <InterpretationCard interpretation={data.contextual_interpretation} />
            )}
          </div>
        )}

        {activeTab === "morphology" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <MorphologyCard morphology={data.morphology} query={data.query} />
          </div>
        )}

        {activeTab === "evidence" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <LiteraryContextCard contexts={data.literary_context} query={data.query} />
            <EvidencePanel sources={data.sources} summary={data.evidence_summary} />
          </div>
        )}

        {activeTab === "related" && (
          <div className="max-w-4xl mx-auto space-y-6">
            <RelatedWordsCard query={data.query} relatedWords={data.related_words} />
          </div>
        )}
      </div>
    </div>
  );
}
