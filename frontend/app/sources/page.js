"use client";

import { useState, useMemo } from "react";
import AppShell from "@/components/layout/AppShell";
import ResourcesHero from "@/components/resources/ResourcesHero";
import ResourceFilters from "@/components/resources/ResourceFilters";
import ResourceCard from "@/components/resources/ResourceCard";
import WorkflowPipeline from "@/components/resources/WorkflowPipeline";

const RESOURCES_DATA = [
  {
    id: "thamizhimorph",
    name: "ThamizhiMorph",
    category: ["morphology"],
    categoryLabel: "Morphology",
    imageWebp: "/resources/resource-thamizhimorph.webp",
    imagePng: "/resources/resource-thamizhimorph.png",
    alt: "ThamizhiMorph — Tamil morphological analysis",
    description:
      "Finite-state morphological analysis for Tamil words. Used to identify roots, grammatical features, and inflected forms before lexical retrieval.",
    example: {
      title: "Example:",
      input: "மரங்களில்",
      output: "→ மரம் + morphological features",
    },
    usedFor: ["Morphology", "Lemma expansion"],
  },
  {
    id: "tamil_wordnet",
    name: "Tamil WordNet",
    category: ["lexical", "semantic"],
    categoryLabel: "Lexical • Semantic",
    imageWebp: "/resources/resource-wordnet.webp",
    imagePng: "/resources/resource-wordnet.png",
    alt: "Tamil WordNet — Lexical network and word relationships",
    description:
      "A Tamil lexical resource providing word relationships and synset information used to support lexical exploration and related-word retrieval.",
    note: "Note: Currently used for word relationships and semantic expansion. Limited gloss availability for WSD.",
    usedFor: ["Word relationships", "Lexical retrieval"],
  },
  {
    id: "thanithamizh_akarathi",
    name: "Thani Thamizh Akarathi",
    category: ["lexical"],
    categoryLabel: "Lexical",
    imageWebp: "/resources/resource-akarathi.webp",
    imagePng: "/resources/resource-akarathi.png",
    alt: "Thani Thamizh Akarathi — Classical Tamil dictionary and lexicon",
    description:
      "A Tamil lexical resource used to retrieve Tamil definitions and lexical information, particularly for classical and pure-Tamil vocabulary.",
    usedFor: ["Lexical definitions", "Meaning retrieval"],
  },
  {
    id: "tamil_wiktionary",
    name: "Tamil Wiktionary",
    category: ["lexical"],
    categoryLabel: "Lexical",
    imageWebp: "/resources/resource-wiktionary.webp",
    imagePng: "/resources/resource-wiktionary.png",
    alt: "Tamil Wiktionary — Polysemous lexical definitions and multiple senses",
    description:
      "Tamil Wiktionary data provides lexical definitions and multiple senses for words, supporting polysemy and contextual word-sense disambiguation.",
    usedFor: ["Lexical senses", "WSD"],
  },
  {
    id: "sentamizh_corpus",
    name: "Sentamizh Corpus",
    category: ["literary"],
    categoryLabel: "Literary",
    imageWebp: "/resources/resource-sentamizh.webp",
    imagePng: "/resources/resource-sentamizh.png",
    alt: "Sentamizh Corpus — Classical Tamil literary evidence and Sangam verses",
    description:
      "A corpus of classical Tamil literary material used to provide textual evidence and examples of word usage in literary contexts.",
    statsRow: {
      verses: "10,393 verses",
      works: "9 works",
    },
    usedFor: ["Literary evidence", "Contextual usage"],
  },
  {
    id: "project_madurai",
    name: "Project Madurai",
    category: ["literary", "semantic"],
    categoryLabel: "Literary • Semantic",
    imageWebp: "/resources/resource-madurai.webp",
    imagePng: "/resources/resource-madurai.png",
    alt: "Project Madurai — Classical Tamil literary retrieval layer",
    description:
      "Provides the literary foundation for SOL AI's classical Tamil retrieval layer. SOL AI indexes selected canonical works for exact retrieval and uses calibrated semantic embeddings for conceptual discovery.",
    statsGrid: {
      works: "35 canonical works",
      releases: "31 releases",
      chunks: "14,383 indexed chunks",
      vectors: "384-dim vectors",
    },
    usedFor: [
      "Exact retrieval",
      "FTS5 search",
      "Semantic retrieval",
      "Classical evidence",
    ],
  },
];

export default function SourcesPage() {
  const [activeFilter, setActiveFilter] = useState("all");

  // Compute counts for filter badges
  const filterCounts = useMemo(() => {
    return {
      all: RESOURCES_DATA.length,
      lexical: RESOURCES_DATA.filter((r) => r.category.includes("lexical")).length,
      morphology: RESOURCES_DATA.filter((r) => r.category.includes("morphology")).length,
      semantic: RESOURCES_DATA.filter((r) => r.category.includes("semantic")).length,
      literary: RESOURCES_DATA.filter((r) => r.category.includes("literary")).length,
    };
  }, []);

  // Filtered resources list
  const filteredResources = useMemo(() => {
    if (activeFilter === "all") return RESOURCES_DATA;
    return RESOURCES_DATA.filter((r) => r.category.includes(activeFilter));
  }, [activeFilter]);

  return (
    <AppShell showSidebar={false} isTransparentHeader={true}>
      <div className="flex-1 w-full relative min-h-[calc(100vh-4rem)] bg-[#020407] text-[#F7F3EA]">
        {/* Subtle Obsidian Gradient Ambient Background */}
        <div className="fixed inset-0 z-0 bg-[#020407] pointer-events-none" />

        <main className="relative z-10 py-6 sm:py-8 lg:py-10 px-4 sm:px-6 lg:px-8 max-w-[1536px] mx-auto w-full space-y-8 sm:space-y-10">
          {/* 1. HERO SECTION */}
          <ResourcesHero resourceCount={RESOURCES_DATA.length} />

          {/* 2. RESOURCE FILTERS */}
          <section className="space-y-4">
            <ResourceFilters
              activeFilter={activeFilter}
              onSelectFilter={setActiveFilter}
              counts={filterCounts}
            />

            {/* 3. RESOURCE CARDS GRID */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 sm:gap-5 items-stretch">
              {filteredResources.map((resource) => (
                <ResourceCard key={resource.id} resource={resource} />
              ))}
            </div>

            {filteredResources.length === 0 && (
              <div className="text-center py-16 bg-[#030508]/90 rounded-2xl border border-[#C9A227]/20 p-8 space-y-2">
                <p className="text-slate-300 font-serif-tamil text-lg">
                  தேர்ந்தெடுக்கப்பட்ட பிரிவில் சான்றுகள் எதுவும் இல்லை.
                </p>
                <button
                  onClick={() => setActiveFilter("all")}
                  className="text-xs text-[#E5C158] hover:underline font-bold"
                >
                  Show all resources
                </button>
              </div>
            )}
          </section>

          {/* 4. "HOW RESOURCES WORK TOGETHER" PROCESS PIPELINE */}
          <WorkflowPipeline />
        </main>
      </div>
    </AppShell>
  );
}
