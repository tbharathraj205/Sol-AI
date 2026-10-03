"use client";

import Image from "next/image";
import {
  FileSearch,
  Sprout,
  Database,
  Network,
  ScrollText,
  Lightbulb,
  ArrowRight,
  Workflow,
} from "lucide-react";

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "User Query",
    description: "A Tamil word is entered for analysis.",
    icon: FileSearch,
  },
  {
    step: "02",
    title: "Morphological Analysis",
    description: "ThamizhiMorph identifies the root, lemma and grammatical features.",
    icon: Sprout,
  },
  {
    step: "03",
    title: "Lexical Retrieval",
    description: "Akarathi, Wiktionary and WordNet provide lexical information and related words.",
    icon: Database,
  },
  {
    step: "04",
    title: "Literary Evidence",
    description: "Sentamizh Corpus and Project Madurai provide textual examples from classical literature.",
    icon: Network,
  },
  {
    step: "05",
    title: "Contextual Analysis",
    description: "Information is combined and ranked based on context and usage.",
    icon: ScrollText,
  },
  {
    step: "06",
    title: "Meaning & Insights",
    description: "Present a unified view with meanings, usage examples and related words.",
    icon: Lightbulb,
  },
];

export default function WorkflowPipeline() {
  return (
    <section className="relative w-full rounded-2xl sm:rounded-3xl border border-[#C9A227]/30 overflow-hidden shadow-[0_10px_40px_rgba(0,0,0,0.8)] bg-[#020407]">
      {/* Exact resource-workflow-bg.png background with 100% opacity, zero blur, zero fog */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/resources/resource-workflow-bg.png"
          alt="Literary workflow pipeline atmospheric backdrop"
          fill
          unoptimized
          priority
          className="object-cover object-center opacity-100"
        />
      </div>

      {/* Main Content */}
      <div className="relative z-10 p-6 sm:p-8 md:p-10 space-y-8">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#C9A227]/15 border border-[#C9A227]/30 flex items-center justify-center text-[#E5C158] shrink-0">
              <Workflow className="w-5 h-5 text-[#E5C158]" />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-bold font-serif-tamil text-[#E5C158] drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]">
                How Resources Work Together
              </h2>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-200 font-sans-tamil max-w-xl md:text-right leading-relaxed drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]">
            SOL AI combines morphological analysis, lexical resources, and
            classical literature to provide meaningful contextual word analysis.
          </p>
        </div>

        {/* 6-Step Horizontal Pipeline (Desktop) / Responsive Grid (Mobile & Tablet) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-6 lg:gap-3 items-start relative">
          {PIPELINE_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isLast = idx === PIPELINE_STEPS.length - 1;

            return (
              <div key={step.step} className="relative flex flex-col group">
                {/* Step Top: Number, Circular Icon, and Desktop Connector Arrow */}
                <div className="flex items-center gap-3 mb-3">
                  {/* Step Number Tag */}
                  <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md bg-[#C9A227]/20 border border-[#C9A227]/40 text-[#E5C158] shadow-sm">
                    {step.step}
                  </span>

                  {/* Circular Gold Icon */}
                  <div className="w-11 h-11 rounded-full border border-[#C9A227]/80 bg-[#020407]/90 flex items-center justify-center text-[#E5C158] shadow-[0_0_14px_rgba(201,162,39,0.25)] group-hover:border-[#E5C158] group-hover:scale-105 transition-all">
                    <Icon className="w-5 h-5 text-[#E5C158]" />
                  </div>

                  {/* Desktop Connecting Arrow */}
                  {!isLast && (
                    <div className="hidden lg:flex flex-1 items-center justify-center pl-1 text-[#C9A227]/70">
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  )}
                </div>

                {/* Step Content: Title & Short Explanation */}
                <div className="space-y-1 pr-2">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-100 group-hover:text-[#E5C158] transition-colors leading-snug drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                    {step.title}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-slate-200 leading-relaxed font-sans-tamil drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
