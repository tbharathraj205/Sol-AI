"use client";

import Image from "next/image";
import { BookOpen } from "lucide-react";

export default function WhatIsSolSection() {
  return (
    <section className="w-full">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
        {/* Left Side: Cinematic Literary Artwork using actual PNG asset */}
        <div className="relative w-full aspect-[16/10] sm:aspect-[16/9] lg:aspect-[4/3] rounded-2xl overflow-hidden border border-[#C9A227]/30 shadow-[0_12px_40px_rgba(0,0,0,0.85)] group">
          <Image
            src="/assets/about/about-literary.png"
            alt="Ancient Tamil palm-leaf manuscripts (olai chuvadi) and traditional brass lamp"
            fill
            sizes="(max-width: 1024px) 100vw, 50vw"
            className="object-cover object-[15%_center] group-hover:scale-105 transition-transform duration-700 ease-out"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#020407]/80 via-transparent to-transparent pointer-events-none" />
        </div>

        {/* Right Side: Text Narrative Content */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#C9A227]/15 border border-[#C9A227]/40 flex items-center justify-center text-[#E5C158] shadow-md shrink-0">
              <BookOpen className="w-5 h-5 text-[#E5C158]" />
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold font-serif-tamil text-[#F7F3EA] tracking-tight">
              What is <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F0D688] to-[#E5C158]">சொல் AI</span>?
            </h2>
          </div>

          <p className="text-base sm:text-lg text-slate-300 font-sans-tamil leading-relaxed">
            சொல் AI is a Tamil Linguistic Intelligence Platform designed to analyze Tamil words beyond simple dictionary lookup. It combines lexical information, morphological analysis, semantic retrieval, contextual word-sense disambiguation, and Classical Tamil literary evidence.
          </p>
        </div>
      </div>
    </section>
  );
}
