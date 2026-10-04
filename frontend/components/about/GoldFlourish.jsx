"use client";

export default function GoldFlourish({ className = "w-48 h-4", variant = "default" }) {
  if (variant === "compact") {
    return (
      <div className={`flex items-center justify-center gap-2 text-[#C9A227]/70 ${className}`}>
        <div className="h-[1px] w-8 bg-gradient-to-r from-transparent to-[#C9A227]/60" />
        <svg
          viewBox="0 0 24 24"
          className="w-3 h-3 fill-none stroke-[#C9A227] stroke-[1.5]"
          aria-hidden="true"
        >
          <path d="M12 4 L14 10 L20 12 L14 14 L12 20 L10 14 L4 12 L10 10 Z" fill="#C9A227" fillOpacity="0.4" />
        </svg>
        <div className="h-[1px] w-8 bg-gradient-to-l from-transparent to-[#C9A227]/60" />
      </div>
    );
  }

  return (
    <div className={`flex items-center justify-center gap-3 text-[#C9A227]/80 ${className}`}>
      <div className="h-[1px] flex-1 max-w-[120px] bg-gradient-to-r from-transparent via-[#C9A227]/40 to-[#C9A227]/80" />
      <svg
        viewBox="0 0 60 16"
        className="w-12 h-3.5 fill-none stroke-[#C9A227] stroke-[1.2]"
        aria-hidden="true"
      >
        {/* Left spiral curl */}
        <path d="M4 8 C10 4, 16 12, 22 8" />
        <circle cx="5" cy="8" r="1.5" fill="#C9A227" />
        {/* Central diamond */}
        <polygon points="30,2 35,8 30,14 25,8" fill="#C9A227" fillOpacity="0.5" stroke="#E5C158" strokeWidth="1" />
        <circle cx="30" cy="8" r="1.2" fill="#FFF5D6" />
        {/* Right spiral curl */}
        <path d="M38 8 C44 4, 50 12, 56 8" />
        <circle cx="55" cy="8" r="1.5" fill="#C9A227" />
      </svg>
      <div className="h-[1px] flex-1 max-w-[120px] bg-gradient-to-l from-transparent via-[#C9A227]/40 to-[#C9A227]/80" />
    </div>
  );
}
