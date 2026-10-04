"use client";

import { Sprout, Layers, BookOpen } from "lucide-react";

const WHY_CARDS = [
  {
    title: "Morphology",
    description:
      "Tamil words can appear in many inflected forms, making direct dictionary lookup insufficient.",
    icon: Sprout,
  },
  {
    title: "Polysemy",
    description:
      "A single word can have multiple meanings depending on how it is used.",
    icon: Layers,
  },
  {
    title: "Literary Context",
    description:
      "Understanding Tamil also involves seeing how words and concepts appear within its literary tradition.",
    icon: BookOpen,
  },
];

export default function WhySolSection() {
  return (
    <section className="w-full pt-6 sm:pt-7 space-y-[1mm]">
      {/* Section Heading */}
      <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold font-serif-tamil text-[#F7F3EA] tracking-tight">
        Why <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F0D688] to-[#E5C158]">SOL AI</span>?
      </h2>

      {/* 3 Cards Grid with max 1mm gap */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-[1mm] items-stretch">
        {WHY_CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              className="flex flex-col justify-between p-6 sm:p-7 rounded-2xl bg-[#060B16]/90 backdrop-blur-md border border-[#C9A227]/30 hover:border-[#C9A227]/70 hover:shadow-[0_8px_30px_rgba(201,162,39,0.12)] transition-all duration-300 group space-y-5"
            >
              {/* Circular Gold Icon Container */}
              <div className="w-12 h-12 rounded-full border border-[#C9A227]/50 bg-[#C9A227]/10 flex items-center justify-center text-[#E5C158] group-hover:border-[#E5C158] group-hover:bg-[#C9A227]/20 group-hover:scale-105 transition-all duration-300 shadow-sm shrink-0">
                <Icon className="w-5 h-5 text-[#E5C158]" />
              </div>

              {/* Title & Description */}
              <div className="space-y-2 flex-1">
                <h3 className="text-xl font-bold font-serif-tamil text-[#F7F3EA] group-hover:text-[#FFF5D6] transition-colors">
                  {card.title}
                </h3>
                <p className="text-sm text-slate-300 font-sans-tamil leading-relaxed">
                  {card.description}
                </p>
              </div>

              {/* Subtle Decorative Gold Accent Line */}
              <div className="h-[1px] w-12 bg-gradient-to-r from-[#C9A227]/40 to-transparent group-hover:w-20 transition-all duration-300" />
            </div>
          );
        })}
      </div>
    </section>
  );
}
