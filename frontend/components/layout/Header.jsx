"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, User, Menu, Puzzle } from "lucide-react";
import { useSidebar } from "./SidebarContext";

export default function Header({ isTransparent = false, showExtensionButton }) {
  const pathname = usePathname();
  const { toggleMobileOpen } = useSidebar();

  const isExplore =
    showExtensionButton !== undefined
      ? showExtensionButton
      : !pathname || pathname === "/" || pathname.startsWith("/search");

  const navLinks = [
    { href: "/", label: "Explore" },
    { href: "/about", label: "About" },
    { href: "/sources", label: "Resources" },
  ];

  const headerBg = isTransparent
    ? "bg-black/50 backdrop-blur-md border-b border-white/5"
    : "bg-black/95 backdrop-blur-md border-b border-white/5 shadow-lg";

  return (
    <header className={`w-full fixed top-0 left-0 right-0 h-16 z-50 transition-colors ${headerBg}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full">
        <div className="flex items-center justify-between h-full">
          {/* Left: Mobile Menu Trigger & Official SOL AI Logo */}
          <div className="flex items-center space-x-3">
            <button
              onClick={toggleMobileOpen}
              className="md:hidden p-2 rounded-lg text-slate-300 hover:text-[#E5C158] hover:bg-white/10 transition cursor-pointer"
              aria-label="Toggle Mobile Menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Official SOL AI Logo -> Clicking navigates to Home / */}
            <Link href="/" className="flex items-center space-x-2 group">
              <img
                src="/navbar_logo.png"
                alt="சொல் AI"
                className="h-10 sm:h-12 w-auto object-contain rounded group-hover:scale-105 transition-transform"
              />
            </Link>
          </div>

          {/* Center Navigation Links */}
          <nav className="hidden md:flex items-center space-x-8 font-serif-tamil text-sm">
            {navLinks.map((link) => {
              const isActive =
                (link.label === "Explore" && (pathname === "/" || pathname.startsWith("/search"))) ||
                (link.label === "About" && pathname === "/about") ||
                (link.label === "Resources" && pathname === "/sources");

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative py-1 transition-colors ${
                    isActive
                      ? "text-[#E5C158] font-semibold border-b-2 border-[#C9A227]"
                      : "text-slate-300 hover:text-[#E5C158]"
                  }`}
                >
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right: Explore page top-right Download சொல் AI Extension button UI */}
          {isExplore ? (
            <button
              type="button"
              className="flex items-center gap-2 sm:gap-2.5 px-3 sm:px-4 py-1.5 rounded-full bg-black/70 hover:bg-black/85 backdrop-blur-md border border-[#C9A227]/60 hover:border-[#E5C158] shadow-[0_0_12px_rgba(201,162,39,0.2)] hover:shadow-[0_0_18px_rgba(201,162,39,0.35)] transition-all duration-200 cursor-pointer select-none group active:scale-[0.98] shrink-0"
              title="Download சொல் AI Extension"
              aria-label="Download சொல் AI Extension"
            >
              {/* Gold SOL AI logo/icon on the LEFT */}
              <img
                src="/sol_emblem.png"
                alt=""
                className="w-4.5 h-4.5 sm:w-5 sm:h-5 object-contain shrink-0 group-hover:scale-105 transition-transform"
              />

              {/* Exact text */}
              <span className="text-xs sm:text-[13px] font-medium text-[#E5C158] font-sans-tamil tracking-wide whitespace-nowrap leading-none flex items-center">
                Download சொல் AI Extension
              </span>

              {/* Gold puzzle-piece icon on the RIGHT */}
              <Puzzle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#E5C158] fill-[#E5C158] shrink-0 group-hover:scale-110 transition-transform" />
            </button>
          ) : (
            <div className="flex items-center space-x-3">
              <button
                className="p-2 rounded-full text-slate-300 hover:text-[#E5C158] hover:bg-white/10 transition cursor-pointer"
                title="Toggle Theme"
              >
                <Sun className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-full text-slate-300 hover:text-[#E5C158] hover:bg-white/10 transition cursor-pointer"
                title="User Profile"
              >
                <User className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
