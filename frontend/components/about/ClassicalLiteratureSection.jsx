"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function ClassicalLiteratureSection() {
  return (
    <section className="relative w-full rounded-2xl sm:rounded-3xl border border-[#C9A227]/30 overflow-hidden shadow-[0_15px_50px_rgba(0,0,0,0.85)] bg-[#020407]">
      {/* Dominant Cinematic Classical Tamil Literature Artwork using actual PNG asset */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/assets/about/about-classical.png"
          alt="Classical Tamil literary heritage with palm leaf manuscripts, temple mandapam, and traditional oil lamp"
          fill
          className="object-cover object-bottom sm:object-[70%_center] opacity-90"
        />
        {/* Dark Left-Side Overlay Gradient for High Text Readability */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#020407] via-[#020407]/90 md:via-[#020407]/75 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#020407] via-transparent to-black/30" />
      </div>

      {/* Content Container */}
      <div className="relative z-10 p-6 sm:p-10 md:p-14 lg:p-16 max-w-2xl space-y-6">
        {/* Major Heading */}
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif-tamil tracking-tight leading-[1.2] drop-shadow-[0_2px_12px_rgba(0,0,0,0.95)]">
          <span className="block text-[#F7F3EA]">
            Grounded in Classical
          </span>
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#F0D688] via-[#E5C158] to-[#C9A227]">
            Tamil Literature
          </span>
        </h2>

        {/* Narrative Description */}
        <p className="text-sm sm:text-base md:text-lg text-slate-200 font-sans-tamil leading-relaxed drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)]">
          SOL AI connects lexical analysis with Classical Tamil literary evidence, allowing users to explore not only what a word means, but how words and concepts appear in literary contexts.
        </p>

        {/* Explore Resources CTA Link */}
        <div className="pt-2">
          <Link
            href="/sources"
            className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-[#0B132B]/90 border border-[#C9A227]/50 text-[#E5C158] hover:text-[#FFF5D6] hover:border-[#E5C158] hover:bg-[#C9A227]/20 transition-all duration-300 shadow-[0_4px_20px_rgba(0,0,0,0.7)] font-medium text-sm sm:text-base group"
          >
            <span>Explore Resources</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </section>
  );
}
