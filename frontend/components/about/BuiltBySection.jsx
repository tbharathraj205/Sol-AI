"use client";

import Image from "next/image";

const TEAM_MEMBERS = [
  {
    name: "Vishwavel Sivakumar",
    handle: "@vishwavel05",
    linkedinUrl: "https://www.linkedin.com/in/vishwavel05",
    avatar: "/assets/about/team-vishwavel.png",
    alt: "Vishwavel Sivakumar",
  },
  {
    name: "Suresh Thevar",
    handle: "@sureshthevar05",
    linkedinUrl: "https://www.linkedin.com/in/sureshthevar05/",
    avatar: "/assets/about/team-suresh.png",
    alt: "Suresh Thevar",
  },
  {
    name: "Bharath Raj T",
    handle: "@tbharathraj205",
    linkedinUrl: "https://www.linkedin.com/in/bharath-raj-t/",
    avatar: "/assets/about/team-bharath-raj-t.png",
    alt: "Bharath Raj T",
  },
];

function LinkedInIcon({ className = "w-3.5 h-3.5", ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
      {...props}
    >
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.45c-.9 0-1.63.73-1.63 1.63s.73 1.63 1.63 1.63 1.63-.73 1.63-1.63c0-.9-.73-1.63-1.63-1.63z" />
    </svg>
  );
}

export default function BuiltBySection() {
  return (
    <section className="w-full pt-6 sm:pt-7 space-y-2.5 sm:space-y-3">
      {/* Section Header with Horizontal Gold Line */}
      <div className="flex items-center gap-4">
        <h2 className="text-xs sm:text-sm font-semibold tracking-[0.25em] text-[#E5C158] uppercase font-sans shrink-0">
          BUILT BY
        </h2>
        <div className="flex-1 h-[1px] bg-gradient-to-r from-[#C9A227]/40 via-[#C9A227]/20 to-transparent" />
      </div>

      {/* 3 Prominent Horizontal Profile Cards with max 1mm gap */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-[1mm] items-stretch">
        {TEAM_MEMBERS.map((member) => (
          <a
            key={member.name}
            href={member.linkedinUrl}
            target="_blank"
            rel="noopener noreferrer"
            title={`${member.name} on LinkedIn`}
            className="group relative flex items-center gap-4 p-4 sm:p-5 h-full rounded-xl sm:rounded-2xl bg-[#060B16]/90 backdrop-blur-md border border-[#C9A227]/30 hover:border-[#C9A227]/80 hover:shadow-[0_8px_30px_rgba(201,162,39,0.15)] transition-all duration-300 overflow-hidden"
          >
            {/* Subtle Decorative Botanical Watermark in Bottom-Right Corner */}
            <div className="absolute -bottom-6 -right-6 w-24 h-24 pointer-events-none opacity-15 group-hover:opacity-25 transition-opacity duration-300">
              <Image
                src="/sidebar_leaf.png"
                alt=""
                width={96}
                height={96}
                className="object-contain filter brightness-125 sepia invert-[0.1]"
                aria-hidden="true"
              />
            </div>

            {/* Circular Profile Avatar using exact same centering for all 3 equal-size pics */}
            <div className="relative w-14 h-14 sm:w-16 sm:h-16 rounded-full overflow-hidden border-2 border-[#C9A227]/60 group-hover:border-[#E5C158] group-hover:scale-105 transition-all duration-300 shadow-md shrink-0 bg-[#0B132B]">
              <Image
                src={member.avatar}
                alt={member.alt}
                fill
                sizes="(max-width: 768px) 56px, 64px"
                className="object-cover"
              />
            </div>

            {/* Member Details */}
            <div className="relative z-10 min-w-0 flex-1 flex flex-col justify-center space-y-0.5 sm:space-y-1">
              <h3 className="text-base sm:text-lg font-bold text-[#F7F3EA] group-hover:text-[#FFF5D6] transition-colors truncate">
                {member.name}
              </h3>
              <div className="flex items-center gap-1.5 text-xs sm:text-sm text-[#E5C158]/80 group-hover:text-[#E5C158] font-sans transition-colors truncate">
                <LinkedInIcon className="w-3.5 h-3.5 shrink-0 text-[#E5C158]/90 group-hover:text-[#E5C158] transition-colors" />
                <span className="truncate">{member.handle}</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
