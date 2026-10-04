"use client";

import Image from "next/image";
import GoldFlourish from "./GoldFlourish";

export default function AboutHero() {
  return (
    <section className="relative w-full rounded-2xl sm:rounded-3xl border border-[#C9A227]/30 overflow-hidden shadow-[0_15px_50px_rgba(0,0,0,0.85)] bg-[#020407]">
      {/* Cinematic Tamil-Literature Landscape Artwork Background using actual PNG asset */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/assets/about/about-hero.png"
          alt="Classical Tamil literary landscape with temple gopuram and sunset"
          fill
          priority
          className="object-cover object-right sm:object-[80%_center] opacity-90"
        />
        {/* Editorial Left-to-Right and Top-to-Bottom Readability Gradients */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#020407] via-[#020407]/90 md:via-[#020407]/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#020407] via-transparent to-black/40" />
      </div>

      {/* Hero Content Container with refined top/bottom spacing */}
      <div className="relative z-10 px-6 sm:px-10 md:px-12 pt-10 sm:pt-14 md:pt-16 pb-8 sm:pb-10 max-w-4xl space-y-4 sm:space-y-5">
        {/* Eyebrow */}
        <div className="inline-block">
          <span className="text-[11px] sm:text-xs font-semibold tracking-[0.28em] text-[#E5C158] uppercase font-sans drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
            ABOUT சொல் AI
          </span>
        </div>

        {/* Main Display Heading */}
        <h1 className="text-3xl sm:text-5xl md:text-6xl font-bold font-serif-tamil tracking-tight leading-[1.15] drop-shadow-[0_2px_12px_rgba(0,0,0,0.9)]">
          <span className="block text-[#F7F3EA]">
            Understanding Tamil,
          </span>
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#F0D688] via-[#E5C158] to-[#C9A227]">
            Beyond the Dictionary
          </span>
        </h1>

        {/* Concise Description */}
        <p className="text-sm sm:text-base md:text-lg text-slate-300 font-sans-tamil leading-relaxed max-w-2xl drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)]">
          Tamil Linguistic Intelligence Platform for lexical, morphological, semantic, and contextual analysis, grounded in Classical Tamil literature.
        </p>

        {/* Symmetrical Gold Flourish Divider */}
        <div className="pt-1">
          <GoldFlourish className="w-56 h-4" />
        </div>
      </div>
    </section>
  );
}
