"use client";

import Image from "next/image";
import { Database } from "lucide-react";

export default function ResourcesHero({ resourceCount = 6 }) {
  return (
    <section className="relative w-full rounded-2xl sm:rounded-3xl border border-[#C9A227]/30 overflow-hidden shadow-[0_10px_40px_rgba(0,0,0,0.8)] bg-[#020407]">
      {/* Exact resources-hero.png background with 100% opacity, zero blur, zero fog */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/resources/resources-hero.png"
          alt="SOL AI linguistic and literary knowledge landscape hero banner"
          fill
          unoptimized
          priority
          className="object-cover object-right opacity-100"
        />
      </div>

      {/* Content Container */}
      <div className="relative z-10 p-6 sm:p-10 md:p-12 lg:p-14 max-w-3xl space-y-5">
        {/* Eyebrow */}
        <div className="inline-block">
          <span className="text-[11px] sm:text-xs font-semibold tracking-[0.25em] text-[#E5C158] uppercase font-sans drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
            RESOURCES
          </span>
        </div>

        {/* Major Headings */}
        <div className="space-y-1 sm:space-y-2">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif-tamil text-transparent bg-clip-text bg-gradient-to-r from-[#FFF5D6] via-[#F0D688] to-[#E5C158] leading-tight drop-shadow-[0_2px_10px_rgba(0,0,0,0.95)]">
            சான்றுகள் &amp; தரவு மூலங்கள்
          </h1>
          <h2 className="text-xl sm:text-2xl md:text-3xl font-medium font-serif-tamil text-[#E5C158] tracking-wide drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]">
            (Evidence &amp; Sources)
          </h2>
        </div>

        {/* Narrative Description */}
        <p className="text-sm sm:text-base text-slate-200 leading-relaxed font-sans-tamil max-w-2xl drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)]">
          SOL AI brings together multiple Tamil linguistic, lexical,
          morphological, and literary resources to provide grounded analysis of
          words and their meanings.
        </p>

        {/* Integrated Resources Counter Badge */}
        <div className="pt-2">
          <div className="inline-flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#030508]/90 border border-[#C9A227]/40 shadow-[0_4px_20px_rgba(0,0,0,0.8)]">
            <div className="w-7 h-7 rounded-lg bg-[#C9A227]/15 flex items-center justify-center text-[#E5C158]">
              <Database className="w-4 h-4 text-[#E5C158]" />
            </div>
            <span className="text-xs sm:text-sm font-medium text-slate-200">
              <span className="font-bold text-[#E5C158]">{resourceCount}</span> linguistic and literary resources currently integrated
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
