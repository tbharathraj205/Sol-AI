"use client";

import { LayoutGrid, BookMarked, Layers, Network, ScrollText } from "lucide-react";

const FILTERS = [
  { id: "all", label: "All", icon: LayoutGrid },
  { id: "lexical", label: "Lexical", icon: BookMarked },
  { id: "morphology", label: "Morphology", icon: Layers },
  { id: "semantic", label: "Semantic", icon: Network },
  { id: "literary", label: "Literary", icon: ScrollText },
];

export default function ResourceFilters({ activeFilter, onSelectFilter, counts = {} }) {
  return (
    <div className="w-full flex items-center gap-2.5 sm:gap-3 overflow-x-auto no-scrollbar py-1">
      {FILTERS.map((f) => {
        const Icon = f.icon;
        const isActive = activeFilter === f.id;
        const count = counts[f.id];

        return (
          <button
            key={f.id}
            type="button"
            onClick={() => onSelectFilter(f.id)}
            aria-pressed={isActive}
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium
              transition-all duration-200 cursor-pointer whitespace-nowrap select-none
              ${
                isActive
                  ? "bg-[#C9A227] text-[#020407] font-bold shadow-[0_2px_12px_rgba(201,162,39,0.35)] scale-[1.02]"
                  : "bg-[#030508]/85 text-slate-300 border border-[#C9A227]/30 hover:border-[#C9A227]/70 hover:text-[#E5C158] hover:bg-white/10"
              }
            `}
          >
            <Icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isActive ? "text-[#020407]" : "text-[#E5C158]"}`} />
            <span>{f.label}</span>
            {count !== undefined && (
              <span
                className={`text-[10px] sm:text-xs px-1.5 py-0.2 rounded-full font-semibold ${
                  isActive
                    ? "bg-[#020407]/20 text-[#020407]"
                    : "bg-white/10 text-slate-400"
                }`}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
