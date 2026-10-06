"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import { Globe, Search, AlertTriangle, ExternalLink, RefreshCw, Layers, FileText, Info } from "lucide-react";
import Link from "next/link";

export default function ExtensionDemoPage() {
  const [activeTab, setActiveTab] = useState("result"); // 'default', 'result', 'error', 'unknown'

  return (
    <AppShell showSidebar={true}>
      <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full space-y-8">
        {/* Title Header */}
        <div className="bg-[#070D19]/90 backdrop-blur-md p-8 rounded-2xl border border-[#C9A227]/30 shadow-xl space-y-4 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C9A227]/20 border border-[#C9A227]/40 text-[#E5C158] text-xs font-bold font-sans-tamil">
              <Globe className="w-4 h-4 text-[#C9A227]" />
              Chrome Extension Showcase (Screens 7, 8, 9)
            </div>
            <h1 className="text-3xl font-bold text-[#F7F3EA] font-sans-tamil">
              சொல் AI பிரவுசர் விரிவாக்கம் (Browser Extension)
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl font-sans-tamil">
              எந்தத் தமிழ் வலைப்பக்கத்திலும் ஒரு சொல்லைத் தேர்ந்தெடுக்கும்போதே (Text Selection), SOL AI உடனடி இலக்கணப் பகுப்பாய்வு மற்றும் சான்றுகளை வழங்கும்.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab("default")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition font-sans-tamil cursor-pointer ${
                activeTab === "default"
                  ? "bg-[#C9A227] text-[#0B132B]"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              7. Default Idle
            </button>
            <button
              onClick={() => setActiveTab("result")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition font-sans-tamil cursor-pointer ${
                activeTab === "result"
                  ? "bg-[#C9A227] text-[#0B132B]"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              8. Result Popup
            </button>
            <button
              onClick={() => setActiveTab("unknown")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition font-sans-tamil cursor-pointer ${
                activeTab === "unknown"
                  ? "bg-[#C9A227] text-[#0B132B]"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              9a. Unknown Word
            </button>
            <button
              onClick={() => setActiveTab("error")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition font-sans-tamil cursor-pointer ${
                activeTab === "error"
                  ? "bg-[#C9A227] text-[#0B132B]"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              9b. Backend Offline
            </button>
          </div>
        </div>

        {/* Extension Frame Container */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Interactive Simulated Extension Popup (5 Cols) */}
          <div className="lg:col-span-5 flex justify-center">
            <div className="w-full max-w-[380px] bg-[#0B132B] text-[#F7F3EA] rounded-2xl shadow-2xl border border-[#C9A227]/40 overflow-hidden font-sans-tamil">
              {/* Chrome Extension Top Bar */}
              <div className="bg-[#050A14] px-4 py-3 border-b border-white/10 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-[#C9A227] flex items-center justify-center font-bold text-[#0B132B] text-xs">
                    சொ
                  </div>
                  <span className="font-bold tracking-wide text-[#E5C158]">SOL AI Extension</span>
                </div>
                <span className="text-[10px] text-[#E5C158] bg-[#C9A227]/20 px-2 py-0.5 rounded font-mono">
                  v1.0.0
                </span>
              </div>

              {/* State 1: Default Idle State */}
              {activeTab === "default" && (
                <div className="p-6 text-center space-y-4">
                  <div className="w-12 h-12 rounded-full bg-[#C9A227]/20 text-[#C9A227] flex items-center justify-center mx-auto">
                    <Search className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-base text-white">சொல்லைத் தேர்ந்தெடுக்கவும்</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    வலைப்பக்கத்தில் உள்ள எந்தத் தமிழ் சொல்லையும் ஹைலைட் செய்யவும் அல்லது கீழே உள்ள தேடல் பெட்டியில் உள்ளிடவும்.
                  </p>
                  <div className="pt-2">
                    <input
                      type="text"
                      placeholder="எ.கா. மரங்களில்..."
                      className="w-full bg-[#050A14] border border-white/15 rounded-xl px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-[#C9A227]"
                    />
                  </div>
                </div>
              )}

              {/* State 2: Result Popup (மரங்களில்) */}
              {activeTab === "result" && (
                <div className="p-5 space-y-4">
                  {/* Selected Word Header */}
                  <div className="bg-[#050A14]/90 p-3.5 rounded-xl border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-[#C9A227] font-semibold uppercase tracking-wider block">
                        Surface Form
                      </span>
                      <span className="text-xl font-bold text-white font-serif-tamil">மரங்களில்</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 block">Lemma</span>
                      <span className="text-sm font-bold text-[#E5C158] bg-[#C9A227]/20 px-2 py-0.5 rounded font-serif-tamil">
                        மரம்
                      </span>
                    </div>
                  </div>

                  {/* Lexical Definition */}
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-[#C9A227] uppercase tracking-wider flex items-center gap-1">
                      <FileText className="w-3 h-3" /> அகராதிப் பொருள் (Definition):
                    </span>
                    <p className="text-xs text-slate-200 bg-[#050A14]/60 p-2.5 rounded-lg border border-white/10 leading-relaxed">
                      தாவர வகையைச் சேர்ந்த பலஆண்டுகள் வாழும் பெரிய தண்டுடைய உறைவிடம்/மரம். (Tree)
                    </p>
                  </div>

                  {/* Morphology Section */}
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-[#E5C158] uppercase tracking-wider flex items-center gap-1">
                      <Layers className="w-3 h-3" /> இலக்கணப் பகுப்பாய்வு (Morphology):
                    </span>
                    <div className="bg-[#050A14]/60 p-2.5 rounded-lg border border-white/10 text-xs space-y-1">
                      <div className="flex justify-between text-slate-300">
                        <span>பகுதி + விகுதி:</span>
                        <span className="font-mono text-[#C9A227]">மரம் + ங்கள் + இல்</span>
                      </div>
                      <div className="flex justify-between text-slate-400 text-[11px]">
                        <span>சொல்லிலக்கணம்:</span>
                        <span>பெயர்ச்சொல் + பன்மை + இடவேற்றுமை</span>
                      </div>
                    </div>
                  </div>

                  {/* Literary Context snippet */}
                  <div className="bg-[#C9A227]/10 p-2.5 rounded-lg border border-[#C9A227]/30 text-xs space-y-1">
                    <span className="text-[10px] font-bold text-[#C9A227]">புறநானூறு #182</span>
                    <p className="italic font-serif-tamil text-slate-300 text-[11px] line-clamp-2">
                      "...மரங்களில் ஓங்கிய சிற சிறகிய புறவின்..."
                    </p>
                  </div>

                  {/* Explore Button */}
                  <Link
                    href="/search?q=மரங்களில்"
                    className="w-full bg-[#C9A227] hover:bg-[#E5C158] text-[#0B132B] font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                  >
                    <span>முழு சான்றுகளையும் காண்க (Explore Full)</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              )}

              {/* State 3: Unknown Word */}
              {activeTab === "unknown" && (
                <div className="p-5 text-center space-y-4">
                  <div className="w-10 h-10 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
                    <Info className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-white">சான்றுகள் கிடைக்கவில்லை</h3>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      SOL AI could not find sufficient evidence for this query in the available resources.
                    </p>
                  </div>
                </div>
              )}

              {/* State 4: Backend Error State */}
              {activeTab === "error" && (
                <div className="p-5 text-center space-y-4">
                  <div className="w-10 h-10 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-white">இணைப்பு தோல்வி (Offline)</h3>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      SOL AI backend services are unavailable at port 8000.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab("result")}
                    className="w-full bg-[#C9A227]/20 hover:bg-[#C9A227]/30 text-[#E5C158] font-bold py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    மீண்டும் முயற்சிக்கவும் (Retry)
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Documentation & Extension Rules (7 Cols) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-[#070D19]/90 backdrop-blur-md p-6 rounded-2xl border border-[#C9A227]/30 shadow-xl space-y-4">
              <h2 className="text-xl font-bold text-[#E5C158] font-sans-tamil flex items-center gap-2">
                <Globe className="w-5 h-5 text-[#C9A227]" />
                பிரவுசர் விரிவாக்கத்தின் இயங்குமுறை (Extension Architecture)
              </h2>
              <p className="text-sm text-slate-300 font-sans-tamil leading-relaxed">
                The SOL AI Chrome Extension operates directly in the browser content script layer. When a user highlights any Tamil text, it sends a query to the backend API (`POST /api/query`) and renders a compact popup using the exact same design tokens (`#0B132B`, `#C9A227`, `#E5C158`, `#F7F3EA`).
              </p>

              <div className="space-y-3 pt-2">
                <div className="p-4 rounded-xl bg-[#050A14]/80 border border-white/10 text-xs space-y-1">
                  <div className="font-bold text-[#E5C158] font-sans-tamil">1. Compact Idle State (Screen 7)</div>
                  <p className="text-slate-400">Quick search bar and word highlight detector ready in Chrome extension toolbar.</p>
                </div>

                <div className="p-4 rounded-xl bg-[#050A14]/80 border border-white/10 text-xs space-y-1">
                  <div className="font-bold text-[#E5C158] font-sans-tamil">2. Result State (Screen 8)</div>
                  <p className="text-slate-400">Displays surface form, root lemma, core/guesser morphology, lexical definition, and Sangam verse snippet with a one-click Explore link to the main web app.</p>
                </div>

                <div className="p-4 rounded-xl bg-[#050A14]/80 border border-white/10 text-xs space-y-1">
                  <div className="font-bold text-[#E5C158] font-sans-tamil">3. Error & Edge States (Screen 9)</div>
                  <p className="text-slate-400">Short actionable messages for unknown words, API timeouts, or offline backend state. Never dumps raw stack traces to the user.</p>
                </div>
              </div>

              <div className="pt-3 border-t border-white/10 flex items-center justify-between flex-wrap gap-4">
                <a
                  href="/sol-ai-extension.zip"
                  download="sol-ai-extension.zip"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#C9A227] to-[#E5C158] hover:from-[#d8ae2b] hover:to-[#edd068] text-[#070D19] font-bold text-xs sm:text-sm shadow-lg shadow-[#C9A227]/20 transition-all transform hover:scale-[1.02] active:scale-[0.98] no-underline"
                >
                  Download சொல் AI Extension (.zip)
                </a>
                <span className="text-xs text-slate-400 font-sans-tamil">
                  Chrome / Edge (Manifest V3)
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
