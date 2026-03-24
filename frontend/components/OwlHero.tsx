"use client";

import { useRef, useState, useEffect, useCallback } from "react";

export default function OwlHero() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [offset, setOffset] = useState({ lx: 0, ly: 0, rx: 0, ry: 0 });

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const svg = svgRef.current;
    if (!svg) return;

    const scleraL = svg.querySelector("#sclera-left");
    const scleraR = svg.querySelector("#sclera-right");
    if (!scleraL || !scleraR) return;

    const rectL = scleraL.getBoundingClientRect();
    const rectR = scleraR.getBoundingClientRect();
    const maxTravel = 6;

    const calc = (rect: DOMRect) => {
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const angle = Math.atan2(dy, dx);
      const dist = Math.min(Math.hypot(dx, dy) / 120, 1);
      return {
        x: Math.cos(angle) * maxTravel * dist,
        y: Math.sin(angle) * maxTravel * dist,
      };
    };

    const l = calc(rectL);
    const r = calc(rectR);
    setOffset({ lx: l.x, ly: l.y, rx: r.x, ry: r.y });
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);

  const pupilStyle = (x: number, y: number): React.CSSProperties => ({
    transform: `translate(${x}px, ${y}px)`,
    transition: "transform 0.1s ease-out",
  });

  return (
    <div className="flex justify-center animate-fade-in mb-[42px]">
      <div className="relative animate-float drop-shadow-[0_0_40px_rgba(37,131,246,0.3)]">
        <svg
          ref={svgRef}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 200 170"
          width={220}
          height={187}
        >
          <g id="clarvia-owl">
            {/* Inner wing color */}
            <path d="M76 102 C56 94, 35 92, 18 94 C26 105, 44 113, 66 114 C72 114, 76 109, 76 102 Z" fill="#59b4ff"/>
            <path d="M124 102 C144 94, 165 92, 182 94 C174 105, 156 113, 134 114 C128 114, 124 109, 124 102 Z" fill="#59b4ff"/>
            {/* Wing feather accents */}
            <path d="M60 101 C49 98, 39 98, 30 100 C38 105, 48 108, 58 108" fill="none" stroke="#1b64d8" strokeWidth="4" strokeLinecap="round"/>
            <path d="M50 105 C40 103, 31 104, 23 107 C31 111, 40 113, 49 113" fill="none" stroke="#1b64d8" strokeWidth="4" strokeLinecap="round"/>
            <path d="M140 101 C151 98, 161 98, 170 100 C162 105, 152 108, 142 108" fill="none" stroke="#1b64d8" strokeWidth="4" strokeLinecap="round"/>
            <path d="M150 105 C160 103, 169 104, 177 107 C169 111, 160 113, 151 113" fill="none" stroke="#1b64d8" strokeWidth="4" strokeLinecap="round"/>
            {/* Body */}
            <ellipse cx="100" cy="104" rx="44" ry="40" fill="#2583f6"/>
            {/* Head tufts */}
            <path d="M79 68 C73 58, 65 56, 60 58 C62 68, 71 74, 79 75 Z" fill="#2583f6"/>
            <path d="M121 68 C127 58, 135 56, 140 58 C138 68, 129 74, 121 75 Z" fill="#2583f6"/>
            {/* Face / belly */}
            <path d="M100 118 C89 118, 79 122, 73 129 C74 142, 85 151, 100 151 C115 151, 126 142, 127 129 C121 122, 111 118, 100 118 Z" fill="#69c7ff"/>
            {/* Small chest feathers */}
            <path d="M84 126 C87 120, 93 119, 97 122 C94 126, 95 131, 100 133 C105 131, 106 126, 103 122 C107 119, 113 120, 116 126 C112 128, 110 132, 111 136 C104 141, 96 141, 89 136 C90 132, 88 128, 84 126 Z" fill="#2583f6"/>
            {/* Eyes — sclera */}
            <ellipse id="sclera-left" cx="80" cy="95" rx="17" ry="19" fill="#ffffff"/>
            <ellipse id="sclera-right" cx="120" cy="95" rx="17" ry="19" fill="#ffffff"/>
            {/* Pupils — these move! */}
            <circle id="pupil-left" cx="84" cy="98" r="8.5" fill="#111111" style={pupilStyle(offset.lx, offset.ly)}/>
            <circle id="pupil-right" cx="116" cy="98" r="8.5" fill="#111111" style={pupilStyle(offset.rx, offset.ry)}/>
            {/* Eye highlights — move with pupils */}
            <circle cx="87.5" cy="93.5" r="2.6" fill="#ffffff" style={pupilStyle(offset.lx, offset.ly)}/>
            <circle cx="119.5" cy="93.5" r="2.6" fill="#ffffff" style={pupilStyle(offset.rx, offset.ry)}/>
            {/* Beak */}
            <path d="M100 98 L92 104 L100 114 L108 104 Z" fill="#f5a623"/>
            <path d="M100 98 L100 114 L92 104 Z" fill="#f7c53b"/>
            {/* Tail */}
            <path d="M92 140 C93 151, 96 159, 100 163 C104 159, 107 151, 108 140 Z" fill="#1f76ec"/>
            {/* Feet */}
            <g fill="#f5a623">
              <ellipse cx="88" cy="146" rx="4.8" ry="6"/>
              <ellipse cx="81" cy="148" rx="4.2" ry="5.4"/>
              <ellipse cx="95" cy="148" rx="4.2" ry="5.4"/>
              <ellipse cx="112" cy="146" rx="4.8" ry="6"/>
              <ellipse cx="105" cy="148" rx="4.2" ry="5.4"/>
              <ellipse cx="119" cy="148" rx="4.2" ry="5.4"/>
            </g>
            {/* Wing outlines */}
            <path d="M78 100 C52 88, 28 84, 12 86 C6 87, 4 96, 9 101 C22 114, 45 123, 70 121" fill="none" stroke="#174fbf" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M122 100 C148 88, 172 84, 188 86 C194 87, 196 96, 191 101 C178 114, 155 123, 130 121" fill="none" stroke="#174fbf" strokeWidth="2.5" strokeLinecap="round"/>
            {/* Body outline */}
            <ellipse cx="100" cy="104" rx="44" ry="40" fill="none" stroke="#174fbf" strokeWidth="2.5"/>
          </g>
        </svg>
      </div>
    </div>
  );
}
