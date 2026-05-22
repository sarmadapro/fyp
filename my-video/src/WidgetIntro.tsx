import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const TEAL = "#0D9488";
const SKY  = "#0EA5E9";
const TEXT = "#0F172A";
const CFG  = { damping: 14, stiffness: 80 } as const;

const WGT_W = 400, WGT_H = 480;
const WGT_START_X = 1920 - WGT_W - 48;
const WGT_START_Y = 1080 - WGT_H - 48;
const WGT_END_X   = (1920 - WGT_W) / 2;
const WGT_END_Y   = 160;
const TAG_Y = WGT_END_Y + WGT_H + 56;

// ── Light-mode cluttered website ──────────────────────────────────────────────
const ClutteredSite: React.FC = () => (
  <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", background: "#FFFFFF" }}>
    {/* Nav bar — packed with links */}
    <div style={{
      height: 60, background: "#FFFFFF",
      borderBottom: "2px solid #E2E8F0",
      display: "flex", alignItems: "center", padding: "0 24px", gap: 4, overflow: "hidden",
    }}>
      <div style={{ width: 110, height: 18, background: "#334155", borderRadius: 4, marginRight: 18, flexShrink: 0 }} />
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} style={{
          width: 92, height: 34, background: i % 3 === 0 ? "#EFF6FF" : "#F8FAFC",
          border: `1px solid ${i % 3 === 0 ? "#BFDBFE" : "#E2E8F0"}`,
          borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0, gap: 5,
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: ["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6"][i % 5], flexShrink: 0 }} />
          <div style={{ width: "50%", height: 7, background: "#CBD5E0", borderRadius: 2 }} />
        </div>
      ))}
      <div style={{ flex: 1 }} />
      <div style={{ width: 88, height: 34, background: "#3B82F6", borderRadius: 6, flexShrink: 0 }} />
      <div style={{ width: 88, height: 34, background: "#EF4444", borderRadius: 6, marginLeft: 6, flexShrink: 0 }} />
    </div>

    {/* Hero banner — cluttered */}
    <div style={{
      height: 160,
      background: "linear-gradient(90deg, #EFF6FF 0%, #F0FDF4 50%, #FFF7ED 100%)",
      display: "flex", alignItems: "center", padding: "0 40px", gap: 32,
      borderBottom: "1px solid #E2E8F0",
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ height: 24, width: "75%", background: "#334155", borderRadius: 4, marginBottom: 10 }} />
        <div style={{ height: 14, width: "55%", background: "#94A3B8", borderRadius: 3, marginBottom: 8 }} />
        <div style={{ height: 10, width: "45%", background: "#CBD5E0", borderRadius: 3, marginBottom: 14 }} />
        <div style={{ display: "flex", gap: 8 }}>
          {["#3B82F6","#10B981","#F59E0B"].map((c, i) => (
            <div key={i} style={{ width: 90, height: 32, background: c, borderRadius: 6, opacity: 0.85 }} />
          ))}
        </div>
      </div>
      <div style={{ width: 240, height: 130, background: "#DBEAFE", borderRadius: 10,
        border: "1px solid #BFDBFE", flexShrink: 0,
        display: "flex", flexDirection: "column", gap: 6, padding: 12,
      }}>
        {[70, 55, 65, 48].map((w, i) => (
          <div key={i} style={{ height: 10, width: `${w}%`, background: "#93C5FD", borderRadius: 2 }} />
        ))}
      </div>
      <div style={{ width: 200, height: 130, background: "#F0FDF4", borderRadius: 10,
        border: "1px solid #A7F3D0", flexShrink: 0,
        display: "flex", flexDirection: "column", gap: 6, padding: 12,
      }}>
        {[60, 75, 50, 65].map((w, i) => (
          <div key={i} style={{ height: 10, width: `${w}%`, background: "#6EE7B7", borderRadius: 2 }} />
        ))}
      </div>
    </div>

    {/* Body */}
    <div style={{ display: "flex", height: 1080 - 60 - 160, overflow: "hidden" }}>
      {/* Sidebar */}
      <div style={{
        width: 220, background: "#F8FAFC",
        borderRight: "1px solid #E2E8F0", padding: "16px 12px", flexShrink: 0, overflow: "hidden",
      }}>
        <div style={{ height: 10, width: "60%", background: "#CBD5E0", borderRadius: 2, marginBottom: 14 }} />
        {[0, 1].map((sec) => (
          <div key={sec} style={{ marginBottom: 14 }}>
            <div style={{ height: 8, width: "45%", background: "#E2E8F0", borderRadius: 2, marginBottom: 8 }} />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{
                height: 30, background: "#FFFFFF", border: "1px solid #E2E8F0",
                borderRadius: 5, marginBottom: 5,
                display: "flex", alignItems: "center", padding: "0 10px", gap: 7,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: ["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6"][(i + sec * 5) % 5], flexShrink: 0 }} />
                <div style={{ width: `${44 + i * 6}%`, height: 7, background: "#E2E8F0", borderRadius: 2 }} />
              </div>
            ))}
            <div style={{ height: 70, background: sec === 0 ? "#DBEAFE" : "#D1FAE5", borderRadius: 6, border: "1px solid #E2E8F0", marginTop: 6 }} />
          </div>
        ))}
      </div>

      {/* 3 content columns */}
      {([
        ["#DBEAFE","#E0F2FE","#EFF6FF"],
        ["#D1FAE5","#DCFCE7","#F0FDF4"],
        ["#FEF3C7","#FDE68A","#FFFBEB"],
      ] as const).map((bgs, col) => (
        <div key={col} style={{
          flex: 1, background: "#FFFFFF",
          borderRight: col < 2 ? "1px solid #E2E8F0" : undefined,
          padding: "14px 12px", overflow: "hidden",
        }}>
          {bgs.map((bg, j) => (
            <React.Fragment key={j}>
              <div style={{ height: [80, 64, 90][j], background: bg, borderRadius: 6, marginBottom: 10,
                border: "1px solid #E2E8F0",
              }} />
              {[82, 68, 58, 74, 50].map((w, k) => (
                <div key={k} style={{
                  height: 9, width: `${w}%`, background: "#E2E8F0",
                  borderRadius: 2, marginBottom: 7,
                }} />
              ))}
            </React.Fragment>
          ))}
        </div>
      ))}
    </div>
  </div>
);

// ── Premium light widget ──────────────────────────────────────────────────────
const WidgetCard: React.FC<{ glowSize: number; frame: number }> = ({ glowSize, frame }) => {
  const dotOp = (i: number) => {
    const t = ((frame - 110 + i * 8) % 24) / 24;
    return 0.25 + 0.75 * Math.abs(Math.sin(t * Math.PI));
  };
  const ansOp = interpolate(frame, [175, 205], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div style={{
      width: WGT_W, height: WGT_H,
      background: "#FFFFFF",
      borderRadius: 20,
      boxShadow: `0 0 0 2px ${TEAL}, 0 0 ${glowSize}px rgba(13,148,136,0.22), 0 0 ${glowSize * 2}px rgba(13,148,136,0.08), 0 24px 60px rgba(15,23,42,0.12)`,
      display: "flex", flexDirection: "column", overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        height: 64, flexShrink: 0,
        background: `linear-gradient(135deg, ${SKY}18, ${TEAL}14)`,
        borderBottom: `2px solid ${TEAL}22`,
        display: "flex", alignItems: "center", padding: "0 20px", gap: 14,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          boxShadow: `0 4px 14px ${TEAL}44`,
        }}>
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
            <rect x="5" y="1" width="6" height="9" rx="3" fill="white" />
            <path d="M2.5 8.5C2.5 11.538 5.462 14 8 14C10.538 14 13.5 11.538 13.5 8.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
            <line x1="8" y1="14" x2="8" y2="15.5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <div style={{ color: TEXT, fontSize: 17, fontWeight: 700 }}>VoiceRAG</div>
          <div style={{ color: TEAL, fontSize: 12, fontWeight: 500 }}>AI Assistant · Ready</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#10B981",
            boxShadow: "0 0 8px #10B981",
          }} />
          <span style={{ fontSize: 12, color: "#10B981", fontWeight: 700, letterSpacing: "0.06em" }}>LIVE</span>
        </div>
      </div>

      {/* Chat */}
      <div style={{ flex: 1, padding: "18px 16px", display: "flex", flexDirection: "column", gap: 14, overflow: "hidden", background: "#FAFBFF" }}>
        {/* Greeting */}
        <div style={{
          background: "#FFFFFF", border: "1px solid #E2E8F0",
          borderLeft: `4px solid ${TEAL}`,
          borderRadius: "2px 14px 14px 14px",
          padding: "12px 16px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
        }}>
          <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.65 }}>
            Hi! I can answer questions about this page instantly.
          </div>
        </div>

        {/* User question */}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <div style={{
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            color: "#FFFFFF",
            padding: "10px 16px", borderRadius: "14px 14px 2px 14px",
            fontSize: 14, lineHeight: 1.45, fontWeight: 500,
            boxShadow: `0 4px 14px ${TEAL}33`,
          }}>
            What are your return policies?
          </div>
        </div>

        {/* Typing dots */}
        {frame >= 110 && frame < 175 && (
          <div style={{ display: "flex", gap: 6, paddingLeft: 4, alignItems: "center" }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{
                width: 10, height: 10, borderRadius: "50%",
                background: TEAL, opacity: dotOp(i),
                boxShadow: `0 0 6px ${TEAL}66`,
              }} />
            ))}
          </div>
        )}

        {/* Answer */}
        {frame >= 175 && (
          <div style={{
            background: "#FFFFFF", border: "1px solid #E2E8F0",
            borderLeft: `4px solid ${TEAL}`,
            borderRadius: "2px 14px 14px 14px",
            padding: "12px 16px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
            opacity: ansOp,
          }}>
            <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.65 }}>
              Returns accepted within 30 days. Contact support with your order number.
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{
        height: 58, borderTop: "1.5px solid #E2E8F0", background: "#FFFFFF",
        display: "flex", alignItems: "center", padding: "0 16px", gap: 10, flexShrink: 0,
      }}>
        <div style={{
          flex: 1, height: 36, background: "#F8FAFC",
          border: `1.5px solid ${TEAL}44`,
          borderRadius: 18, display: "flex", alignItems: "center", padding: "0 14px",
          fontSize: 13, color: "#94A3B8",
        }}>
          Ask anything…
        </div>
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
          flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: `0 4px 12px ${TEAL}44`,
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M3 8L13 3L10 8L13 13L3 8Z" fill="white" />
          </svg>
        </div>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const WidgetIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Site enters (0-40)
  const siteSpr     = spring({ frame, fps, config: CFG, durationInFrames: 40 });
  const siteOpacity = interpolate(siteSpr, [0, 1], [0, 1]);

  // Widget slides in (82-122)
  const wgtEnterSpr = spring({ frame: Math.max(0, frame - 82), fps, config: CFG, durationInFrames: 40 });
  const wgtOpacity  = interpolate(wgtEnterSpr, [0, 1], [0, 1]);
  const wgtInitY    = interpolate(wgtEnterSpr, [0, 1], [32, 0]);

  // Site fades out (140-178)
  const siteFade = interpolate(frame, [140, 178], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Widget centers (185-228)
  const centerSpr = spring({ frame: Math.max(0, frame - 185), fps, config: CFG, durationInFrames: 43 });
  const wgtX      = interpolate(centerSpr, [0, 1], [WGT_START_X, WGT_END_X]);
  const wgtY      = interpolate(centerSpr, [0, 1], [WGT_START_Y, WGT_END_Y]);
  const glowSize  = interpolate(centerSpr, [0, 1], [28, 80]);
  const spotOp    = interpolate(centerSpr, [0, 1], [0, 0.14]);

  // Taglines (232+)
  const tag1Spr = spring({ frame: Math.max(0, frame - 232), fps, config: CFG, durationInFrames: 30 });
  const tag2Spr = spring({ frame: Math.max(0, frame - 250), fps, config: CFG, durationInFrames: 30 });
  const tag1Op  = interpolate(tag1Spr, [0, 1], [0, 1]);
  const tag1TY  = interpolate(tag1Spr, [0, 1], [26, 0]);
  const tag2Op  = interpolate(tag2Spr, [0, 1], [0, 1]);
  const tag2TY  = interpolate(tag2Spr, [0, 1], [26, 0]);

  // Sub tagline (265+)
  const subSpr = spring({ frame: Math.max(0, frame - 265), fps, config: CFG, durationInFrames: 28 });
  const subOp  = interpolate(subSpr, [0, 1], [0, 1]);

  return (
    <AbsoluteFill style={{
      background: "#F8FAFF",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      {/* Site */}
      {frame < 180 && (
        <div style={{ opacity: siteOpacity * siteFade }}>
          <ClutteredSite />
        </div>
      )}

      {/* Teal spotlight when widget centers */}
      {frame >= 185 && (
        <div style={{
          position: "absolute",
          left: WGT_END_X + WGT_W / 2 - 400,
          top: WGT_END_Y + WGT_H / 2 - 400,
          width: 800, height: 800, borderRadius: "50%",
          background: `radial-gradient(circle, rgba(13,148,136,${spotOp}) 0%, transparent 70%)`,
          filter: "blur(80px)", pointerEvents: "none",
        }} />
      )}

      {/* Widget */}
      <div style={{
        position: "absolute",
        left: wgtX,
        top: wgtY + wgtInitY,
        opacity: wgtOpacity,
      }}>
        <WidgetCard glowSize={glowSize} frame={frame} />
      </div>

      {/* Taglines */}
      {frame >= 230 && (
        <div style={{
          position: "absolute", left: 0, width: "100%", top: TAG_Y,
          textAlign: "center",
        }}>
          <div style={{
            fontSize: 80, fontWeight: 800, color: TEXT,
            letterSpacing: "-0.03em", lineHeight: 1.1,
            opacity: tag1Op, transform: `translateY(${tag1TY}px)`,
          }}>
            Stop searching.
          </div>
          <div style={{
            fontSize: 80, fontWeight: 800,
            letterSpacing: "-0.03em", lineHeight: 1.1,
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            opacity: tag2Op, transform: `translateY(${tag2TY}px)`,
          }}>
            Just ask.
          </div>
          <div style={{
            marginTop: 20, fontSize: 20, color: "#64748B",
            letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 500,
            opacity: subOp,
          }}>
            One widget. Any website. Instant answers.
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};