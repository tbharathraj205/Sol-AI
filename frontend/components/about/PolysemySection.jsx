"use client";

import Image from "next/image";
import GoldFlourish from "./GoldFlourish";

export default function PolysemySection() {
  return (
    <section className="w-full pt-6 sm:pt-7 space-y-2.5 sm:space-y-3">
      {/* Small Compact Section Heading — Uniform Gold Serif */}
      <h2 className="text-base sm:text-lg md:text-xl font-bold font-serif-tamil text-transparent bg-clip-text bg-gradient-to-r from-[#F0D688] via-[#E5C158] to-[#C9A227] tracking-tight">
        The Same Word. Different Meaning.
      </h2>

      {/* Compact Four-Part Horizontal Composition filling full webpage width */}
      <div className="flex flex-col lg:flex-row items-center gap-3 sm:gap-4 lg:gap-5 w-full">
        {/* 1. Left: "கால்" Tamil Display Word with Single Gold Flourish Below */}
        <div className="flex flex-col items-center justify-center shrink-0 w-auto min-w-[90px] lg:w-32 py-1">
          <span className="text-3xl sm:text-4xl font-bold font-serif-tamil text-transparent bg-clip-text bg-gradient-to-b from-[#FFF5D6] via-[#F0D688] to-[#C9A227] tracking-wider leading-none drop-shadow-[0_2px_10px_rgba(201,162,39,0.3)]">
            கால்
          </span>
          <GoldFlourish className="w-20 sm:w-24 h-3 mt-1.5 opacity-90" />
        </div>

        {/* 2 & 3. Middle: Two Meaning Cards expanding to fill width, with images filling entire cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 flex-1 w-full min-w-0">
          {/* Example 1 Card: Fraction / Measurement */}
          <div className="relative overflow-hidden rounded-xl border border-[#C9A227]/30 hover:border-[#C9A227]/70 transition-all duration-300 shadow-md group min-h-[76px] sm:min-h-[84px] flex items-center bg-[#040812]">
            {/* Background image filling the entire card */}
            <div className="absolute inset-0 z-0">
              <Image
                src="/assets/about/wsd-grain.png"
                alt="Tamil measurement context — கால் கிலோ grains in measuring bowl"
                fill
                sizes="(max-width: 768px) 100vw, 40vw"
                className="object-cover object-right sm:object-center group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#040812]/95 via-[#040812]/80 via-40% to-[#040812]/20" />
            </div>

            {/* Content over image */}
            <div className="relative z-10 px-4 py-3 sm:px-5 sm:py-3.5 space-y-0.5">
              <h3 className="text-sm sm:text-[15px] font-bold font-serif-tamil text-[#F7F3EA] group-hover:text-[#FFF5D6] transition-colors leading-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
                கால் கிலோ
              </h3>
              <p className="text-[11px] sm:text-xs text-[#E5C158] font-sans font-medium leading-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
                ¼ kilogram / 250g
              </p>
            </div>
          </div>

          {/* Example 2 Card: Body / Locomotion */}
          <div className="relative overflow-hidden rounded-xl border border-[#C9A227]/30 hover:border-[#C9A227]/70 transition-all duration-300 shadow-md group min-h-[76px] sm:min-h-[84px] flex items-center bg-[#040812]">
            {/* Background image filling the entire card */}
            <div className="absolute inset-0 z-0">
              <Image
                src="/assets/about/wsd-feet.png"
                alt="Tamil anatomical and movement context — கால் walking feet on stone"
                fill
                sizes="(max-width: 768px) 100vw, 40vw"
                className="object-cover object-right sm:object-center group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#040812]/95 via-[#040812]/80 via-40% to-[#040812]/20" />
            </div>

            {/* Content over image */}
            <div className="relative z-10 px-4 py-3 sm:px-5 sm:py-3.5 space-y-0.5">
              <h3 className="text-sm sm:text-[15px] font-bold font-serif-tamil text-[#F7F3EA] group-hover:text-[#FFF5D6] transition-colors leading-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
                கால்
              </h3>
              <p className="text-[11px] sm:text-xs text-[#E5C158] font-sans font-medium leading-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.8)]">
                foot / leg
              </p>
            </div>
          </div>
        </div>

        {/* 4. Far Right: Vertical Divider & Contextual Explanation */}
        <div className="flex items-center gap-3 lg:gap-4 shrink-0 w-full lg:w-auto lg:max-w-[260px] xl:max-w-[300px] pt-1 lg:pt-0">
          <div className="hidden lg:block w-px h-10 bg-[#C9A227]/40 shrink-0" />
          <p className="text-xs text-[#C5C2BA] font-sans-tamil leading-relaxed">
            SOL AI uses surrounding context to distinguish between competing meanings of a polysemous Tamil word.
          </p>
        </div>
      </div>
    </section>
  );
}
