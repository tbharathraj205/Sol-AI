"use client";

import AppShell from "@/components/layout/AppShell";
import AboutHero from "@/components/about/AboutHero";
import BuiltBySection from "@/components/about/BuiltBySection";
import WhatIsSolSection from "@/components/about/WhatIsSolSection";
import WhySolSection from "@/components/about/WhySolSection";
import PolysemySection from "@/components/about/PolysemySection";
import ClassicalLiteratureSection from "@/components/about/ClassicalLiteratureSection";

export default function AboutPage() {
  return (
    <AppShell showSidebar={false} isTransparentHeader={true}>
      <div className="flex-1 w-full relative min-h-[calc(100vh-4rem)] bg-[#020407] text-[#F7F3EA]">
        {/* Subtle Ambient Obsidian Background Layer */}
        <div className="fixed inset-0 z-0 bg-[#020407] pointer-events-none" />

        <main className="relative z-10 py-2 sm:py-3 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full space-y-[1mm]">
          {/* 1. Hero Section */}
          <AboutHero />

          {/* 2. Built By — Prominent Team Section */}
          <BuiltBySection />

          {/* 3. What is சொல் AI? */}
          <WhatIsSolSection />

          {/* 4. Why சொல் AI? */}
          <WhySolSection />

          {/* 5. The Same Word. Different Meaning. */}
          <PolysemySection />

          {/* 6. Grounded in Classical Tamil Literature */}
          <ClassicalLiteratureSection />
        </main>
      </div>
    </AppShell>
  );
}
