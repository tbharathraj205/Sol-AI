"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, User, Menu } from "lucide-react";
import { useSidebar } from "./SidebarContext";

export default function Header({ isTransparent = false }) {
  const pathname = usePathname();
  const { toggleMobileOpen } = useSidebar();

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

          {/* Right Utilities: Sun Theme Icon & Profile Avatar Icon */}
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
        </div>
      </div>
    </header>
  );
}
