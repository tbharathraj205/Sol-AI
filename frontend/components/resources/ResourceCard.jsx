"use client";

import Image from "next/image";
import {
  GitBranch,
  Network,
  BookOpen,
  FileText,
  Scroll,
  Landmark,
  Info,
  Layers,
  Compass,
  Bookmark,
  Library,
} from "lucide-react";

// Icon mapping for primary resource icons
const RESOURCE_ICONS = {
  thamizhimorph: GitBranch,
  tamil_wordnet: Network,
  thanithamizh_akarathi: BookOpen,
  tamil_wiktionary: FileText,
  sentamizh_corpus: Scroll,
  project_madurai: Landmark,
};

// Category badge styles
const BADGE_STYLES = {
  Morphology: {
    bg: "bg-teal-950/85 text-teal-300 border-teal-500/40",
  },
  "Lexical • Semantic": {
    bg: "bg-amber-950/85 text-amber-300 border-amber-500/40",
  },
  Lexical: {
    bg: "bg-sky-950/85 text-sky-300 border-sky-500/40",
  },
  Literary: {
    bg: "bg-purple-950/85 text-purple-300 border-purple-500/40",
  },
  "Literary • Semantic": {
    bg: "bg-indigo-950/90 text-purple-200 border-purple-400/40",
  },
};

export default function ResourceCard({ resource }) {
  const Icon = RESOURCE_ICONS[resource.id] || BookOpen;
  const isMadurai = resource.id === "project_madurai";
  const badgeStyle = BADGE_STYLES[resource.categoryLabel] || {
    bg: "bg-slate-900/80 text-slate-300 border-slate-700/50",
  };

  return (
    <div
      className={`
        bg-[#030508]/95 backdrop-blur-md rounded-2xl overflow-hidden flex flex-col justify-between
        transition-all duration-300 group select-none
        ${
          isMadurai
            ? "border-2 border-[#C9A227]/45 hover:border-[#E5C158] shadow-[0_6px_28px_rgba(201,162,39,0.12)] hover:shadow-[0_12px_36px_rgba(201,162,39,0.25)] hover:-translate-y-1.5"
            : "border border-[#C9A227]/25 hover:border-[#C9A227]/70 shadow-[0_6px_24px_rgba(0,0,0,0.7)] hover:shadow-[0_12px_32px_rgba(201,162,39,0.15)] hover:-translate-y-1.5"
        }
      `}
    >
      {/* 1. ARTWORK AREA */}
      <div className="relative w-full aspect-[4/3] overflow-hidden bg-[#020407]">
        <Image
          src={resource.imagePng || resource.imageWebp}
          alt={resource.alt}
          fill
          unoptimized
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 33vw, 16vw"
          className="object-cover object-center group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />

        {/* Gradient overlay for smooth transition into card body */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#030508] via-transparent to-black/25 pointer-events-none" />

        {/* Category Badge anchored near bottom-left of artwork */}
        <div className="absolute bottom-2.5 left-3 z-10">
          <span
            className={`
              inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10px] sm:text-[11px] font-semibold border backdrop-blur-md shadow-sm
              ${badgeStyle.bg}
            `}
          >
            {resource.categoryLabel}
          </span>
        </div>
      </div>

      {/* 2. CARD CONTENT AREA */}
      <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-4">
        {/* Top: Title & Description */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded flex items-center justify-center text-[#E5C158] shrink-0">
              <Icon className="w-4 h-4 text-[#E5C158]" />
            </div>
            <h3 className="text-sm sm:text-base font-bold font-serif-tamil text-[#E5C158] tracking-tight leading-snug">
              {resource.name}
            </h3>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans-tamil line-clamp-4">
            {resource.description}
          </p>
        </div>

        {/* Middle: Optional Content Block (Example, Note, Stats) */}
        <div className="min-h-[44px] flex flex-col justify-center">
          {/* ThamizhiMorph Example Box */}
          {resource.example && (
            <div className="bg-[#020407]/90 border border-white/10 rounded-lg p-2.5 text-[11px] text-slate-300 font-mono space-y-0.5">
              <div className="text-[10px] text-slate-400 font-sans uppercase tracking-wider">
                {resource.example.title}
              </div>
              <div className="text-[#E5C158] font-bold font-sans-tamil">
                {resource.example.input}
              </div>
              <div className="text-slate-400 text-[10px] font-sans-tamil">
                {resource.example.output}
              </div>
            </div>
          )}

          {/* Tamil WordNet Note Box */}
          {resource.note && (
            <div className="bg-amber-950/20 border border-amber-500/25 rounded-lg p-2 text-[11px] text-amber-200/90 leading-snug flex items-start gap-1.5">
              <Info className="w-3.5 h-3.5 text-[#E5C158] shrink-0 mt-0.5" />
              <span>{resource.note}</span>
            </div>
          )}

          {/* Sentamizh Corpus Stats */}
          {resource.statsRow && (
            <div className="grid grid-cols-2 gap-2 p-2 rounded-lg bg-[#020407]/90 border border-white/10 text-[11px] text-slate-300">
              <div className="flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-[#E5C158] shrink-0" />
                <span className="font-semibold text-slate-200 truncate">{resource.statsRow.verses}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Library className="w-3.5 h-3.5 text-[#E5C158] shrink-0" />
                <span className="font-semibold text-slate-200 truncate">{resource.statsRow.works}</span>
              </div>
            </div>
          )}

          {/* Project Madurai Stats Grid */}
          {resource.statsGrid && (
            <div className="grid grid-cols-2 gap-1.5 p-2 rounded-lg bg-[#020407]/95 border border-[#C9A227]/30 text-[10px] text-slate-300">
              <div className="flex items-center gap-1">
                <BookOpen className="w-3 h-3 text-[#E5C158] shrink-0" />
                <span className="truncate">{resource.statsGrid.works}</span>
              </div>
              <div className="flex items-center gap-1">
                <Bookmark className="w-3 h-3 text-[#E5C158] shrink-0" />
                <span className="truncate">{resource.statsGrid.releases}</span>
              </div>
              <div className="flex items-center gap-1">
                <Layers className="w-3 h-3 text-[#E5C158] shrink-0" />
                <span className="truncate">{resource.statsGrid.chunks}</span>
              </div>
              <div className="flex items-center gap-1">
                <Compass className="w-3 h-3 text-[#E5C158] shrink-0" />
                <span className="truncate">{resource.statsGrid.vectors}</span>
              </div>
            </div>
          )}
        </div>

        {/* Bottom: "Used for:" Tags */}
        <div className="space-y-1.5 pt-2 border-t border-white/10">
          <div className="text-[11px] font-semibold text-slate-400">
            Used for:
          </div>
          <div className="flex flex-wrap gap-1.5">
            {resource.usedFor.map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 rounded-md bg-[#020407] border border-[#C9A227]/25 text-slate-300 group-hover:border-[#C9A227]/40 transition-colors"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
