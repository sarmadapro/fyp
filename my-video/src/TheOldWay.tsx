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
const TEXT = "#0F172A";
const SUB  = "#64748B";
const CFG  = { damping: 12, stiffness: 80 } as const;

// ── Browser geometry ──────────────────────────────────────────────────────────
const BW = { x: 140, y: 60, w: 1640, h: 920 };
const CHROME_H  = 52;
const NAV_H     = 64;
const SIDEBAR_W = 260;
const CONTENT_TOP = CHROME_H + NAV_H;
const CONTENT_H   = BW.h - CONTENT_TOP;

const CLICKS: { frame: number; x: number; y: number }[] = [
  { frame: 80,  x: BW.x + 100,  y: BW.y + CHROME_H + 32 },
  { frame: 108, x: BW.x + 390,  y: BW.y + CHROME_H + 32 },
  { frame: 136, x: BW.x + 680,  y: BW.y + CHROME_H + 32 },
  { frame: 158, x: BW.x + 120,  y: BW.y + CONTENT_TOP + 120 },
];
const X_BTN   = { x: BW.x + BW.w - 26, y: BW.y + 24 };
const X_CLICK = 182;

const CKF: [number, number, number][] = [
  [58,  BW.x + 820, BW.y + 480],
  [70,  BW.x + 38,  BW.y + CHROME_H + 16],
  [80,  CLICKS[0].x, CLICKS[0].y],
  [93,  BW.x + 660, BW.y + 430],
  [108, CLICKS[1].x, CLICKS[1].y],
  [121, BW.x + 1050, BW.y + 560],
  [136, CLICKS[2].x, CLICKS[2].y],
  [144, BW.x + 80,  BW.y + CONTENT_TOP + 70],
  [158, CLICKS[3].x, CLICKS[3].y],
  [170, X_BTN.x,    X_BTN.y],
  [188, X_BTN.x,    X_BTN.y],
];

// Rotating saturated palettes for the cluttered content
const PALETTES: string[][] = [
  ["#BFDBFE","#DBEAFE","#93C5FD","#E0F2FE","#BAE6FD","#7DD3FC","#E5E7EB","#F3F4F6"],
  ["#A5B4FC","#C7D2FE","#818CF8","#E0E7FF","#C4B5FD","#A78BFA","#F3F4F6","#EDE9FE"],
  ["#FCA5A5","#FECACA","#F87171","#FEE2E2","#FDBA74","#FCD34D","#F3F4F6","#FEF2F2"],
  ["#6EE7B7","#A7F3D0","#34D399","#D1FAE5","#86EFAC","#4ADE80","#E5E7EB","#F0FDF4"],
  ["#FDE68A","#FEF3C7","#FCD34D","#FFFBEB","#FED7AA","#FDBA74","#F9FAFB","#FFFBEB"],
];

function getShake(frame: number): number {
  return CLICKS.reduce((acc, c) => {
    const t = frame - c.frame;
    if (t < 0 || t > 14) return acc;
    return acc + Math.sin(t * 2.2) * (1 - t / 14) * 8;
  }, 0);
}

function getVignette(frame: number): number {
  const pct = CLICKS.filter((c) => frame >= c.frame).length / CLICKS.length;
  return pct * 0.32;
}

// ── Cursor SVG ────────────────────────────────────────────────────────────────
const CursorSVG: React.FC = () => (
  <svg width="34" height="42" viewBox="0 0 20 28" style={{ display: "block", filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.35))" }}>
    <path
      d="M 1 1 L 1 21 L 5 17 L 9 25 L 12 24 L 8 16 L 14 16 Z"
      fill="#1E293B"
      stroke="rgba(255,255,255,0.9)"
      strokeWidth="1.2"
      strokeLinejoin="round"
    />
  </svg>
);

// ── Click ripple ──────────────────────────────────────────────────────────────
const ClickRipple: React.FC<{
  frame: number; clickFrame: number; x: number; y: number; color?: string;
}> = ({ frame, clickFrame, x, y, color = "rgba(14,165,233,0.6)" }) => {
  const t = (frame - clickFrame) / 22;
  if (t < 0 || t > 1) return null;
  const r = t * 56;
  return (
    <div style={{
      position: "absolute", left: x - r, top: y - r,
      width: r * 2, height: r * 2, borderRadius: "50%",
      border: `2px solid ${color}`, opacity: (1 - t) * 0.85,
      pointerEvents: "none", zIndex: 200,
    }} />
  );
};

// ── Browser chrome ────────────────────────────────────────────────────────────
const BrowserChrome: React.FC<{ showX: boolean; xOp: number; clickState: number }> = ({ showX, xOp, clickState }) => (
  <div style={{
    position: "absolute", left: 0, top: 0, width: BW.w, height: CHROME_H,
    background: "#1E293B",
    display: "flex", alignItems: "center",
    padding: "0 16px", boxSizing: "border-box", zIndex: 10, gap: 0,
  }}>
    {/* Traffic lights */}
    {(["#FF5F57","#FFBD2E","#28C840"] as const).map((col, i) => (
      <div key={i} style={{ width: 14, height: 14, borderRadius: "50%", background: col, marginRight: 8, flexShrink: 0,
        boxShadow: i === 0 && showX ? `0 0 10px ${col}` : "none",
      }} />
    ))}
    {/* Tabs */}
    {Array.from({ length: 4 }).map((_, i) => (
      <div key={i} style={{
        width: 140, height: 32, flexShrink: 0, marginLeft: i === 0 ? 20 : 4,
        background: i === 0 ? "#334155" : "#1E293B",
        borderRadius: "6px 6px 0 0",
        border: i === 0 ? "1px solid #475569" : "1px solid #2D3748",
        borderBottom: "none",
        display: "flex", alignItems: "center", padding: "0 10px", gap: 6,
      }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: ["#3B82F6","#10B981","#F59E0B","#EF4444"][i], flexShrink: 0 }} />
        <div style={{ flex: 1, height: 7, background: "#475569", borderRadius: 2 }} />
        {i === 0 && <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#64748B", flexShrink: 0 }} />}
      </div>
    ))}
    {/* Address bar */}
    <div style={{ flex: 1, marginLeft: 16, height: 30, background: "#0F172A", borderRadius: 6,
      display: "flex", alignItems: "center", padding: "0 12px", gap: 8,
    }}>
      <div style={{ width: 12, height: 12, borderRadius: "50%", border: "1.5px solid #475569", flexShrink: 0 }} />
      <div style={{ flex: 1, height: 7, background: "#334155", borderRadius: 2 }} />
    </div>
    {/* Loading spinner for active clicks */}
    {clickState > 0 && clickState < 4 && (
      <div style={{
        width: 18, height: 18, borderRadius: "50%",
        border: "2px solid #475569",
        borderTop: "2px solid #38BDF8",
        marginLeft: 12, flexShrink: 0,
        animation: "spin 0.7s linear infinite",
      }} />
    )}
    {showX && (
      <div style={{
        width: 28, height: 28, borderRadius: "50%", background: "#EF4444",
        boxShadow: "0 0 16px 5px rgba(239,68,68,0.7), 0 0 32px 12px rgba(239,68,68,0.3)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 13, color: "white", fontWeight: "bold", opacity: xOp, flexShrink: 0, marginLeft: 12,
      }}>✕</div>
    )}
  </div>
);

// ── Nav bar ───────────────────────────────────────────────────────────────────
const NavBar: React.FC<{ clickState: number }> = ({ clickState }) => (
  <div style={{
    position: "absolute", left: 0, top: CHROME_H, width: BW.w, height: NAV_H,
    background: "#FFFFFF", borderBottom: "2px solid #E2E8F0",
    display: "flex", alignItems: "center", padding: "0 16px", gap: 4, overflow: "hidden",
  }}>
    {/* Logo area */}
    <div style={{ width: 120, height: 36, background: "#EFF6FF", borderRadius: 6, marginRight: 16,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{ width: "60%", height: 10, background: "#3B82F6", borderRadius: 2 }} />
    </div>
    {Array.from({ length: 8 }).map((_, i) => (
      <div key={i} style={{
        width: 128, height: 38, flexShrink: 0,
        background: i < clickState ? "#EFF6FF" : "#F8FAFC",
        border: `1.5px solid ${i < clickState ? "#93C5FD" : "#E2E8F0"}`,
        borderRadius: 6,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
      }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: i < clickState ? "#3B82F6" : "#CBD5E0", flexShrink: 0 }} />
        <div style={{ width: "50%", height: 8, background: i < clickState ? "#60A5FA" : "#CBD5E0", borderRadius: 2 }} />
      </div>
    ))}
    <div style={{ flex: 1 }} />
    {/* Search bar in nav */}
    <div style={{ width: 180, height: 34, background: "#F1F5F9", borderRadius: 17,
      border: "1px solid #E2E8F0", display: "flex", alignItems: "center", padding: "0 12px", gap: 6, flexShrink: 0,
    }}>
      <div style={{ width: 12, height: 12, borderRadius: "50%", border: "1.5px solid #94A3B8", flexShrink: 0 }} />
      <div style={{ flex: 1, height: 7, background: "#CBD5E0", borderRadius: 2 }} />
    </div>
    <div style={{ width: 90, height: 34, background: "#3B82F6", borderRadius: 6, marginLeft: 8, flexShrink: 0 }} />
  </div>
);

// ── Sidebar ───────────────────────────────────────────────────────────────────
const Sidebar: React.FC<{ palette: string[] }> = ({ palette }) => (
  <div style={{
    width: SIDEBAR_W, height: CONTENT_H, flexShrink: 0,
    background: "#F8FAFC", borderRight: "2px solid #E2E8F0",
    padding: "18px 14px", boxSizing: "border-box",
    display: "flex", flexDirection: "column", overflow: "hidden",
  }}>
    <div style={{ height: 10, width: "55%", background: "#94A3B8", borderRadius: 3, marginBottom: 18, flexShrink: 0 }} />
    {/* Category sections */}
    {[0, 1].map((section) => (
      <div key={section} style={{ marginBottom: 16 }}>
        <div style={{ height: 8, width: "40%", background: "#CBD5E0", borderRadius: 2, marginBottom: 10 }} />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{
            height: 34, background: "#FFFFFF", border: "1px solid #E2E8F0",
            borderRadius: 6, marginBottom: 6, display: "flex", alignItems: "center",
            padding: "0 12px", boxSizing: "border-box", flexShrink: 0, gap: 8,
          }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: palette[(i+section*4) % palette.length], flexShrink: 0 }} />
            <div style={{ width: `${44 + i * 7}%`, height: 8, background: "#E2E8F0", borderRadius: 2 }} />
          </div>
        ))}
      </div>
    ))}
    {[palette[4], palette[6], palette[2]].map((bg, i) => (
      <div key={i} style={{ height: [80, 64, 50][i], background: bg, borderRadius: 6, marginBottom: 8, flexShrink: 0, border: "1px solid #E2E8F0" }} />
    ))}
  </div>
);

// ── Content column ────────────────────────────────────────────────────────────
const ContentCol: React.FC<{ idx: number; palette: string[] }> = ({ idx, palette }) => {
  const c = (i: number) => palette[(i + idx * 2) % palette.length];
  const bannerH = [100, 60, 120][idx];
  const imgH    = [130, 110, 96][idx];
  const textRow = (w: number, key: number) => (
    <div key={key} style={{ height: 9, width: `${w}%`, background: "#E2E8F0", borderRadius: 2, marginBottom: 7, flexShrink: 0 }} />
  );
  const block = (h: number, ci: number) => (
    <div style={{ height: h, background: c(ci), marginBottom: 8, flexShrink: 0, borderRadius: 4, border: "1px solid #E2E8F0" }} />
  );
  return (
    <div style={{
      flex: 1, height: CONTENT_H, padding: "12px 10px", boxSizing: "border-box",
      borderRight: idx < 2 ? "1px solid #E2E8F0" : undefined,
      display: "flex", flexDirection: "column", overflow: "hidden", background: "#FFFFFF",
    }}>
      {block(bannerH, 0)}
      {[88, 70, 84, 56, 74].map((w, i) => textRow(w, i))}
      {block(imgH, 2)}
      {[80, 64, 76, 50, 68].map((w, i) => textRow(w, i + 10))}
      {block(64, 3)}
      {[74, 58, 86, 42].map((w, i) => textRow(w, i + 20))}
      {block(84, 4)}
      {[82, 66, 74, 50].map((w, i) => textRow(w, i + 30))}
      {block(54, 5)}
      {[78, 60, 72].map((w, i) => textRow(w, i + 40))}
      {block(100, 6)}
      {[70, 54, 68].map((w, i) => textRow(w, i + 50))}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const TheOldWay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enterSpr   = spring({ frame, fps, config: CFG, durationInFrames: 55 });
  const enterScale = interpolate(enterSpr, [0, 1], [0.88, 1.0]);
  const enterOp    = interpolate(enterSpr, [0, 1], [0, 1]);

  const exitRel    = Math.max(0, frame - X_CLICK);
  const exitSpr    = spring({ frame: exitRel, fps, config: { damping: 10, stiffness: 120 } });
  const isExiting  = frame >= X_CLICK;
  const exitScale  = interpolate(exitSpr, [0, 1], [1.0, 0.0], { extrapolateRight: "clamp" });
  const exitOp     = interpolate(exitSpr, [0, 1], [1.0, 0.0], { extrapolateRight: "clamp" });
  const exitRot    = interpolate(exitSpr, [0, 1], [0, 4],    { extrapolateRight: "clamp" });

  const bScale = isExiting ? exitScale : frame < 55 ? enterScale : 1.0;
  const bOp    = isExiting ? exitOp    : frame < 55 ? enterOp    : 1.0;
  const bRot   = isExiting ? exitRot   : 0;

  const showBrowser = frame < 215;

  const showCursor = frame >= 58 && frame < 200;
  const cf   = Math.min(Math.max(frame, CKF[0][0]), CKF[CKF.length - 1][0]);
  const curX = interpolate(cf, CKF.map(k => k[0]), CKF.map(k => k[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const curY = interpolate(cf, CKF.map(k => k[0]), CKF.map(k => k[2]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const clickState = CLICKS.filter(c => frame >= c.frame).length;
  const palette    = PALETTES[clickState % PALETTES.length];

  const xBtnRel = Math.max(0, frame - 162);
  const xBtnSpr = spring({ frame: xBtnRel, fps, config: CFG });
  const showX   = frame >= 162;
  const shakeX  = getShake(frame);
  const vignetteOp = getVignette(frame);

  // "They just gave up." — cinematic
  const textDelay = 218;
  const textSpr   = spring({ frame: Math.max(0, frame - textDelay), fps, config: { damping: 18, stiffness: 60 } });
  const textOp    = interpolate(textSpr, [0, 1], [0, 1]);
  const textY     = interpolate(textSpr, [0, 1], [36, 0]);

  const subDelay = 238;
  const subSpr   = spring({ frame: Math.max(0, frame - subDelay), fps, config: { damping: 18, stiffness: 60 } });
  const subOp    = interpolate(subSpr, [0, 1], [0, 1]);

  const flashOp = interpolate(frame, [X_CLICK, X_CLICK + 6, X_CLICK + 20], [0, 0.28, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 90% 60% at 50% 50%, #EFF6FF 0%, #F8FAFF 100%)",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      {/* Red flash on close */}
      <div style={{
        position: "absolute", left: 0, top: 0, width: "100%", height: "100%",
        background: "#EF4444", opacity: flashOp, pointerEvents: "none", zIndex: 300,
      }} />

      {/* Frustration red vignette */}
      {vignetteOp > 0 && (
        <div style={{
          position: "absolute", left: 0, top: 0, width: "100%", height: "100%",
          background: `radial-gradient(ellipse at center, transparent 35%, rgba(220,38,38,${vignetteOp}) 100%)`,
          pointerEvents: "none", zIndex: 250,
        }} />
      )}

      {/* Browser window */}
      {showBrowser && (
        <div style={{
          position: "absolute", left: BW.x + shakeX, top: BW.y,
          width: BW.w, height: BW.h,
          borderRadius: 12, overflow: "hidden",
          opacity: bOp,
          transform: `scale(${bScale}) rotate(${bRot}deg)`,
          transformOrigin: "center center",
          boxShadow: "0 32px 80px rgba(15,23,42,0.22), 0 8px 24px rgba(15,23,42,0.12), 0 0 0 1px rgba(15,23,42,0.08)",
        }}>
          <BrowserChrome showX={showX} xOp={xBtnSpr} clickState={clickState} />
          <NavBar clickState={clickState} />
          <div style={{
            position: "absolute", left: 0, top: CONTENT_TOP, width: BW.w, height: CONTENT_H,
            display: "flex", overflow: "hidden",
          }}>
            <Sidebar palette={palette} />
            <ContentCol idx={0} palette={palette} />
            <ContentCol idx={1} palette={palette} />
            <ContentCol idx={2} palette={palette} />
          </div>
        </div>
      )}

      {/* Click ripples */}
      {CLICKS.map((c, i) => (
        <ClickRipple key={i} frame={frame} clickFrame={c.frame} x={c.x + shakeX} y={c.y} />
      ))}
      <ClickRipple frame={frame} clickFrame={X_CLICK} x={X_BTN.x} y={X_BTN.y} color="rgba(239,68,68,0.85)" />

      {/* Cursor */}
      {showCursor && (
        <div style={{
          position: "absolute", left: curX + shakeX, top: curY,
          pointerEvents: "none", zIndex: 100,
        }}>
          <CursorSVG />
        </div>
      )}

      {/* Finale */}
      {frame >= textDelay && (
        <div style={{
          position: "absolute", width: "100%", top: "50%",
          transform: `translateY(calc(-50% + ${textY}px))`,
          textAlign: "center", opacity: textOp,
        }}>
          <div style={{
            fontSize: 108, fontWeight: 800, color: TEXT,
            letterSpacing: "-0.03em", lineHeight: 1.05,
          }}>
            They just gave up.
          </div>
          <div style={{
            marginTop: 28, fontSize: 22, color: SUB,
            letterSpacing: "0.18em", textTransform: "uppercase", fontWeight: 600,
            opacity: subOp,
          }}>
            Sound familiar?
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};