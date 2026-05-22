import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── Brand palette ─────────────────────────────────────────────────────────────
const BG   = "#F8FAFF";
const TEAL = "#0D9488";
const SKY  = "#0EA5E9";
const TEXT = "#0F172A";
const SUB  = "#64748B";
const CFG  = { damping: 14, stiffness: 75 } as const;

const QUESTION = "What is your refund policy?";
const ANSWER   = "Refunds accepted within 30 days. Contact support with your order number — processed in 2 business days.";

// ── Laptop geometry ───────────────────────────────────────────────────────────
const SCR  = { x: 480, y: 110, w: 960, h: 600 };
const BASE = { x: 456, y: 710, w: 1008, h: 62 };
const HINGE = { x: 456, y: 710, w: 1008, h: 8 };

const WGT_W = 380, WGT_H = 460;
const WGT_X = SCR.x + SCR.w - WGT_W - 20;
const WGT_Y = SCR.y + (SCR.h - WGT_H) / 2 + 10;

// ── Floating grid dots (subtle on light bg) ───────────────────────────────────
function GridDots({ frame }: { frame: number }) {
  const dots = Array.from({ length: 60 }, (_, i) => {
    const x    = (i * 137.5) % 100;
    const y    = (((i * 97.3) % 100) + frame * (0.015 + (i % 7) * 0.003)) % 100;
    const size = 2 + (i % 3);
    const op   = 0.06 + (i % 5) * 0.025;
    const col  = i % 3 === 0 ? SKY : TEAL;
    return { x, y, size, op, col };
  });
  return (
    <>
      {dots.map((p, i) => (
        <div key={i} style={{
          position: "absolute", left: `${p.x}%`, top: `${p.y}%`,
          width: p.size, height: p.size, borderRadius: "50%",
          background: p.col, opacity: p.op, pointerEvents: "none",
        }} />
      ))}
    </>
  );
}

// ── VoiceRAG Widget (full detail) ─────────────────────────────────────────────
const WidgetCard: React.FC<{ frame: number; qLen: number; showDots: boolean; ansOp: number; showWave: boolean; waveRel: number; inputFocus: boolean }> = ({
  frame, qLen, showDots, ansOp, showWave, waveRel, inputFocus,
}) => {
  const dotOp = (off: number) => {
    const t = ((frame - 174 + off) % 22) / 22;
    return 0.25 + 0.75 * Math.abs(Math.sin(t * Math.PI));
  };

  return (
    <div style={{
      width: WGT_W, height: WGT_H,
      background: "#FFFFFF",
      borderRadius: 16,
      boxShadow: `0 0 0 1.5px ${TEAL}, 0 12px 48px rgba(13,148,136,0.2), 0 4px 16px rgba(0,0,0,0.08)`,
      display: "flex", flexDirection: "column", overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        height: 56, flexShrink: 0,
        background: `linear-gradient(135deg, ${SKY}18, ${TEAL}14)`,
        borderBottom: `1.5px solid ${TEAL}33`,
        display: "flex", alignItems: "center", padding: "0 18px", gap: 12,
      }}>
        {/* Brand icon */}
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          boxShadow: `0 4px 12px ${TEAL}44`,
        }}>
          {/* Mic icon */}
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="5" y="1" width="6" height="9" rx="3" fill="white" />
            <path d="M2.5 8.5C2.5 11.538 5.462 14 8 14C10.538 14 13.5 11.538 13.5 8.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
            <line x1="8" y1="14" x2="8" y2="15.5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <div style={{ color: TEXT, fontSize: 15, fontWeight: 700, letterSpacing: "0.02em" }}>VoiceRAG</div>
          <div style={{ color: TEAL, fontSize: 11, fontWeight: 500 }}>AI Assistant · Online</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#10B981",
            boxShadow: "0 0 6px #10B981", flexShrink: 0,
          }} />
          <span style={{ fontSize: 11, color: "#10B981", fontWeight: 600 }}>LIVE</span>
        </div>
      </div>

      {/* Chat area */}
      <div style={{
        flex: 1, padding: "16px 14px", display: "flex", flexDirection: "column", gap: 12, overflow: "hidden",
        background: "#FAFBFF",
      }}>
        {/* Bot greeting */}
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: `linear-gradient(135deg, ${SKY}33, ${TEAL}22)`,
            border: `1px solid ${TEAL}44`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: TEAL }} />
          </div>
          <div style={{
            background: "#FFFFFF", border: "1px solid #E2E8F0",
            borderLeft: `3px solid ${TEAL}`,
            borderRadius: "2px 12px 12px 12px",
            padding: "10px 14px", maxWidth: "85%",
            boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
          }}>
            <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>
              Hi! Ask me anything about this website. I'll answer instantly.
            </div>
          </div>
        </div>

        {/* User question */}
        {qLen > 0 && (
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <div style={{
              background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
              color: "#FFFFFF",
              padding: "10px 16px", borderRadius: "14px 14px 2px 14px",
              fontSize: 13, lineHeight: 1.5, fontWeight: 500,
              boxShadow: `0 4px 14px ${TEAL}33`,
              maxWidth: "85%",
            }}>
              {QUESTION.slice(0, qLen)}
              <span style={{ opacity: 0.7 }}>|</span>
            </div>
          </div>
        )}

        {/* Typing dots */}
        {showDots && (
          <div style={{ display: "flex", gap: 6, paddingLeft: 36, alignItems: "center" }}>
            {[0, 7, 14].map((off, i) => (
              <div key={i} style={{
                width: 9, height: 9, borderRadius: "50%",
                background: TEAL, opacity: dotOp(off),
                boxShadow: `0 0 6px ${TEAL}66`,
              }} />
            ))}
          </div>
        )}

        {/* Answer */}
        {frame >= 196 && (
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: `linear-gradient(135deg, ${SKY}33, ${TEAL}22)`,
              border: `1px solid ${TEAL}44`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: TEAL }} />
            </div>
            <div style={{
              background: "#FFFFFF", border: "1px solid #E2E8F0",
              borderLeft: `3px solid ${TEAL}`,
              borderRadius: "2px 12px 12px 12px",
              padding: "10px 14px",
              boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
              opacity: ansOp, maxWidth: "85%",
            }}>
              <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.65 }}>{ANSWER}</div>
              {showWave && (
                <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ position: "relative", width: 22, height: 22 }}>
                    {[0, 1].map((j) => {
                      const t = ((waveRel + j * 20) % 56) / 56;
                      return (
                        <div key={j} style={{
                          position: "absolute", left: 0, top: 0, width: 22, height: 22,
                          borderRadius: "50%", border: `1.5px solid ${TEAL}`,
                          transform: `scale(${1 + t * 2.8})`, opacity: (1 - t) * 0.7,
                        }} />
                      );
                    })}
                    <div style={{ position: "absolute", left: 4, top: 4, width: 14, height: 14,
                      borderRadius: "50%", background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
                    }} />
                  </div>
                  {/* Voice bars */}
                  <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
                    {[0, 1, 2, 3, 4].map((i) => {
                      const h = 8 + Math.abs(Math.sin(((waveRel + i * 7) / 22) * Math.PI)) * 16;
                      return (
                        <div key={i} style={{
                          width: 4, height: h, borderRadius: 2,
                          background: `linear-gradient(to top, ${SKY}, ${TEAL})`,
                        }} />
                      );
                    })}
                  </div>
                  <span style={{ fontSize: 12, color: TEAL, fontWeight: 600 }}>Speaking…</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div style={{
        height: 54, borderTop: "1.5px solid #E2E8F0", background: "#FFFFFF",
        display: "flex", alignItems: "center", padding: "0 14px", gap: 10, flexShrink: 0,
      }}>
        <div style={{
          flex: 1, height: 36, background: "#F8FAFC",
          border: `1.5px solid ${inputFocus ? TEAL : "#E2E8F0"}`,
          borderRadius: 18, display: "flex", alignItems: "center", padding: "0 14px",
          fontSize: 13, color: "#94A3B8",
          boxShadow: inputFocus ? `0 0 0 3px ${TEAL}18` : "none",
        }}>
          Ask anything…
        </div>
        {/* Mic button */}
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
          flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: `0 4px 12px ${TEAL}44`,
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <rect x="5" y="1" width="6" height="9" rx="3" fill="white" />
            <path d="M2.5 8.5C2.5 11.538 5.462 14 8 14C10.538 14 13.5 11.538 13.5 8.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
          </svg>
        </div>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const TheNewWay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Laptop enters (0-55)
  const lapSpr   = spring({ frame, fps, config: CFG, durationInFrames: 55 });
  const lapOp    = interpolate(lapSpr, [0, 1], [0, 1]);
  const lapScale = interpolate(lapSpr, [0, 1], [0.86, 1.0]);

  // Screen illuminates (55-100)
  const illuminSpr  = spring({ frame: Math.max(0, frame - 55), fps, config: CFG, durationInFrames: 45 });
  const screenLight = interpolate(illuminSpr, [0, 1], [0, 1]);

  // Widget slides in (100-135)
  const wgtSpr = spring({ frame: Math.max(0, frame - 100), fps, config: CFG, durationInFrames: 35 });
  const wgtOp  = interpolate(wgtSpr, [0, 1], [0, 1]);
  const wgtTY  = interpolate(wgtSpr, [0, 1], [28, 0]);

  // Question types (140-174)
  const qLen = Math.floor(interpolate(frame, [140, 174], [0, QUESTION.length], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  }));

  const showDots = frame >= 174 && frame < 196;
  const ansOp    = interpolate(frame, [196, 218], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const showWave = frame >= 230 && frame < 278;
  const waveRel  = Math.max(0, frame - 230);
  const inputFocus = frame >= 138 && frame < 176;

  // Tagline (284-300)
  const tagSpr = spring({ frame: Math.max(0, frame - 284), fps, config: CFG, durationInFrames: 32 });
  const tagOp  = interpolate(tagSpr, [0, 1], [0, 1]);
  const tagTY  = interpolate(tagSpr, [0, 1], [32, 0]);

  const screenR = Math.round(interpolate(screenLight, [0, 1], [20, 248]));
  const screenG = Math.round(interpolate(screenLight, [0, 1], [24, 250]));
  const screenB = Math.round(interpolate(screenLight, [0, 1], [36, 255]));
  const screenBg = `rgb(${screenR},${screenG},${screenB})`;

  const glowOp = interpolate(screenLight, [0, 1], [0, 0.16]);

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 100% 70% at 50% 40%, #EFF6FF 0%, #F8FAFF 100%)",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      <GridDots frame={frame} />

      {/* Ambient glow behind laptop */}
      <div style={{
        position: "absolute",
        left: SCR.x + SCR.w / 2 - 340,
        top: SCR.y + SCR.h / 2 - 340,
        width: 680, height: 680, borderRadius: "50%",
        background: `radial-gradient(circle, rgba(13,148,136,${glowOp}) 0%, transparent 70%)`,
        filter: "blur(60px)", opacity: lapOp, pointerEvents: "none",
      }} />

      {/* Laptop */}
      <div style={{
        position: "absolute", left: 0, top: 0, width: "100%", height: "100%",
        opacity: lapOp, transform: `scale(${lapScale})`, transformOrigin: "center center",
      }}>
        {/* Screen lid (silver aluminum) */}
        <div style={{
          position: "absolute", left: SCR.x - 16, top: SCR.y - 16,
          width: SCR.w + 32, height: SCR.h + 32,
          background: "linear-gradient(160deg, #CBD5E0 0%, #B8C5D0 60%, #A0B0BC 100%)",
          borderRadius: "16px 16px 4px 4px",
          boxShadow: "0 40px 100px rgba(15,23,42,0.18), 0 8px 24px rgba(15,23,42,0.1)",
        }}>
          {/* Apple-style logo notch */}
          <div style={{
            position: "absolute", left: "50%", top: 10,
            transform: "translateX(-50%)",
            width: 24, height: 24, borderRadius: "50%",
            background: "rgba(148,163,184,0.5)",
          }} />
        </div>

        {/* Screen bezel (thin inner frame) */}
        <div style={{
          position: "absolute", left: SCR.x, top: SCR.y,
          width: SCR.w, height: SCR.h,
          background: "#1E293B",
          borderRadius: 8, overflow: "hidden",
        }}>
          {/* Screen content */}
          <div style={{
            width: "100%", height: "100%",
            background: screenBg, overflow: "hidden", position: "relative",
          }}>
            {/* Mini browser chrome */}
            <div style={{
              height: 38, background: "#F1F5F9", borderBottom: "1px solid #E2E8F0",
              display: "flex", alignItems: "center", padding: "0 14px", gap: 6, flexShrink: 0,
            }}>
              {(["#FF5F57","#FFBD2E","#28C840"] as const).map((c, i) => (
                <div key={i} style={{ width: 11, height: 11, borderRadius: "50%", background: c }} />
              ))}
              <div style={{ flex: 1, marginLeft: 12, height: 20, background: "#E2E8F0", borderRadius: 3 }} />
            </div>
            {/* Page body */}
            <div style={{ flex: 1, padding: "18px 20px", overflow: "hidden" }}>
              <div style={{ height: 18, width: "55%", background: "#334155", borderRadius: 3, marginBottom: 12 }} />
              {[72, 54, 66, 42, 60, 36, 54].map((w, i) => (
                <div key={i} style={{ height: 9, width: `${w}%`, background: "#E2E8F0", borderRadius: 2, marginBottom: 9 }} />
              ))}
              <div style={{ height: 60, background: "#DBEAFE", borderRadius: 6, margin: "12px 0" }} />
              {[62, 48, 56].map((w, i) => (
                <div key={i} style={{ height: 9, width: `${w}%`, background: "#E2E8F0", borderRadius: 2, marginBottom: 9 }} />
              ))}
            </div>

            {/* Widget */}
            <div style={{
              position: "absolute", right: 18, bottom: 18,
              opacity: wgtOp, transform: `translateY(${wgtTY}px)`,
            }}>
              <WidgetCard
                frame={frame} qLen={qLen}
                showDots={showDots} ansOp={ansOp}
                showWave={showWave} waveRel={waveRel}
                inputFocus={inputFocus}
              />
            </div>
          </div>
        </div>

        {/* Keyboard base */}
        <div style={{
          position: "absolute", left: BASE.x, top: BASE.y, width: BASE.w, height: BASE.h,
          background: "linear-gradient(180deg, #B8C5D0 0%, #A8B8C4 100%)",
          borderRadius: "0 0 12px 12px",
          boxShadow: "0 20px 60px rgba(15,23,42,0.15)",
        }}>
          {/* Trackpad */}
          <div style={{
            position: "absolute", left: BASE.w / 2 - 80, top: 12,
            width: 160, height: 36, background: "#A8B8C4", borderRadius: 6,
            border: "1px solid #94A3B8",
          }} />
        </div>

        {/* Hinge shadow line */}
        <div style={{
          position: "absolute", left: HINGE.x, top: HINGE.y, width: HINGE.w, height: HINGE.h,
          background: "linear-gradient(180deg, rgba(15,23,42,0.15) 0%, transparent 100%)",
        }} />
      </div>

      {/* Tagline */}
      {frame >= 282 && (
        <div style={{
          position: "absolute", width: "100%", bottom: 80,
          textAlign: "center", opacity: tagOp,
          transform: `translateY(${tagTY}px)`,
        }}>
          <span style={{ fontSize: 92, fontWeight: 800, color: TEXT, letterSpacing: "-0.03em" }}>
            The new{" "}
          </span>
          <span style={{
            fontSize: 92, fontWeight: 800, letterSpacing: "-0.03em",
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            way.
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};