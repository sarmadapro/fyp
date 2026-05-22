import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const TEAL  = "#0D9488";
const SKY   = "#0EA5E9";
const TEXT  = "#0F172A";
const SUB   = "#64748B";
const MUTED = "#94A3B8";
const CFG   = { damping: 14, stiffness: 80 } as const;

const NODE_R  = 90;
const NODE_Y  = 500;
const NODES = [
  { x: 310,  label: "Retrieve",  sub: "Vector Search",   timing: "~15ms",  color: SKY  },
  { x: 770,  label: "Rank",      sub: "Top-K Filter",    timing: "~8ms",   color: "#8B5CF6" },
  { x: 1230, label: "Generate",  sub: "LLM Synthesis",   timing: "~800ms", color: "#F59E0B" },
  { x: 1690, label: "Speak",     sub: "Kokoro TTS",      timing: "~200ms", color: TEAL  },
];

const STAGE_F = [55, 120, 185, 250];
const LINE_F  = [88, 153, 218];

// ── SVG node icons ────────────────────────────────────────────────────────────
const RetrieveIcon: React.FC<{ active: boolean }> = ({ active }) => {
  const c = active ? SKY : MUTED;
  return (
    <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
      <circle cx="10" cy="10" r="6" stroke={c} strokeWidth="2.2" />
      <line x1="14.5" y1="14.5" x2="20" y2="20" stroke={c} strokeWidth="2.2" strokeLinecap="round" />
      {active && (
        <>
          <circle cx="10" cy="10" r="3" fill={`${SKY}33`} />
          <circle cx="10" cy="10" r="1.5" fill={SKY} />
        </>
      )}
    </svg>
  );
};

const RankIcon: React.FC<{ active: boolean; rel: number }> = ({ active, rel }) => {
  const c = active ? "#8B5CF6" : MUTED;
  const bars = active ? [
    interpolate(rel, [0, 20], [4, 40], { extrapolateRight: "clamp" }),
    interpolate(rel, [8, 28], [4, 28], { extrapolateRight: "clamp" }),
    interpolate(rel, [16, 36], [4, 18], { extrapolateRight: "clamp" }),
  ] : [14, 10, 6];
  return (
    <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
      <rect x="3" y={24 - bars[0]} width="5" height={bars[0]} rx="1.5" fill={c} />
      <rect x="10" y={24 - bars[1]} width="5" height={bars[1]} rx="1.5" fill={c} opacity={0.8} />
      <rect x="17" y={24 - bars[2]} width="5" height={bars[2]} rx="1.5" fill={c} opacity={0.6} />
      {active && <path d="M2 4L12 2L22 4" stroke={c} strokeWidth="1.5" strokeLinecap="round" opacity={0.5} />}
    </svg>
  );
};

const GenerateIcon: React.FC<{ active: boolean; rel: number }> = ({ active, rel }) => {
  const c = active ? "#F59E0B" : MUTED;
  const pulse = active ? 0.5 + 0.5 * Math.sin((rel / 18) * Math.PI * 2) : 0;
  return (
    <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L14.5 8.5H21L15.75 12.5L17.5 19L12 15.5L6.5 19L8.25 12.5L3 8.5H9.5L12 2Z"
        stroke={c} strokeWidth="1.8" strokeLinejoin="round"
        fill={active ? `rgba(245,158,11,${0.12 + pulse * 0.12})` : "none"}
      />
      {active && (
        <circle cx="12" cy="11" r="3" fill="none" stroke={c} strokeWidth="1" opacity={0.4 + pulse * 0.4} />
      )}
    </svg>
  );
};

const SpeakIcon: React.FC<{ active: boolean; rel: number }> = ({ active, rel }) => {
  const c = active ? TEAL : MUTED;
  return (
    <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
      <path d="M3 9H7L12 4V20L7 15H3V9Z" stroke={c} strokeWidth="2" strokeLinejoin="round"
        fill={active ? `${TEAL}22` : "none"}
      />
      {active && (
        <>
          <path d="M16 7C17.5 8.5 18.5 10.2 18.5 12C18.5 13.8 17.5 15.5 16 17" stroke={c} strokeWidth="2" strokeLinecap="round" />
          <path d="M19 5C21.5 7.5 23 9.7 23 12C23 14.3 21.5 16.5 19 19" stroke={c} strokeWidth="2" strokeLinecap="round" opacity={0.5 + 0.5 * Math.sin((rel / 22) * Math.PI * 2)} />
        </>
      )}
    </svg>
  );
};

// ── Animated data packet ──────────────────────────────────────────────────────
function DataPacket({ startX, endX, y, startFrame, frame, color }: {
  startX: number; endX: number; y: number; startFrame: number; frame: number; color: string;
}) {
  const p = interpolate(frame, [startFrame, startFrame + 32], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  if (p <= 0 || p >= 1) return null;
  const x  = interpolate(p, [0, 1], [startX, endX]);
  const op = p < 0.1 ? p * 10 : p > 0.9 ? (1 - p) * 10 : 1;
  const trail = [0.6, 0.3, 0.1].map((to, i) => ({
    x: x - (i + 1) * 16 * (p > 0 ? 1 : -1),
    op: op * to,
    r: 7 - i * 2,
  }));
  return (
    <>
      {trail.map((t, i) => (
        <div key={i} style={{
          position: "absolute", left: t.x - t.r, top: y - t.r,
          width: t.r * 2, height: t.r * 2, borderRadius: "50%",
          background: color, opacity: t.op, pointerEvents: "none",
        }} />
      ))}
      <div style={{
        position: "absolute", left: x - 7, top: y - 7,
        width: 14, height: 14, borderRadius: "50%",
        background: color, opacity: op,
        boxShadow: `0 0 16px ${color}, 0 0 32px ${color}66`,
        pointerEvents: "none",
      }} />
    </>
  );
}

// ── Ripple rings from node ────────────────────────────────────────────────────
function RippleRings({ cx, cy, r, color, frame, startFrame }: {
  cx: number; cy: number; r: number; color: string; frame: number; startFrame: number;
}) {
  if (frame < startFrame) return null;
  const rel = frame - startFrame;
  return (
    <>
      {[0, 20, 40].map((offset, i) => {
        const t = ((rel + offset) % 60) / 60;
        const cr = r + t * 80;
        return (
          <div key={i} style={{
            position: "absolute",
            left: cx - cr, top: cy - cr,
            width: cr * 2, height: cr * 2,
            borderRadius: "50%",
            border: `2px solid ${color}`,
            opacity: (1 - t) * 0.4,
            pointerEvents: "none",
          }} />
        );
      })}
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export const PipelineDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const spr = (startF: number) =>
    spring({ frame: Math.max(0, frame - startF), fps, config: CFG, durationInFrames: 34 });

  const nodeSpr = STAGE_F.map((f) => spr(f));

  const lineP = (startF: number) =>
    interpolate(frame, [startF, startF + 32], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });

  const headerOp = interpolate(frame, [0, 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const queryOp  = interpolate(frame, [24, 52], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const underSpr = spring({ frame: Math.max(0, frame - 272), fps, config: CFG, durationInFrames: 32 });
  const underOp  = interpolate(underSpr, [0, 1], [0, 1]);
  const underTY  = interpolate(underSpr, [0, 1], [28, 0]);

  const cursorOn = Math.floor(frame / 14) % 2 === 0;

  // Timing badge opacity per connector
  const timingOp = (i: number) =>
    interpolate(frame, [LINE_F[i] + 30, LINE_F[i] + 50], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 110% 80% at 50% -10%, rgba(14,165,233,0.06) 0%, #F8FAFF 45%)",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      {/* Subtle grid */}
      <svg style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", opacity: 0.06, pointerEvents: "none" }}>
        {Array.from({ length: 22 }).map((_, i) => (
          <line key={`v${i}`} x1={i * 92} y1={0} x2={i * 92} y2={1080} stroke={TEAL} strokeWidth={0.8} />
        ))}
        {Array.from({ length: 13 }).map((_, i) => (
          <line key={`h${i}`} x1={0} y1={i * 90} x2={1920} y2={i * 90} stroke={TEAL} strokeWidth={0.8} />
        ))}
      </svg>

      {/* Header */}
      <div style={{ position: "absolute", top: 68, width: "100%", textAlign: "center", opacity: headerOp }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 10,
          background: "rgba(255,255,255,0.9)",
          border: "1px solid #E2E8F0",
          borderRadius: 100,
          padding: "8px 24px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: TEAL, boxShadow: `0 0 8px ${TEAL}` }} />
          <span style={{
            fontFamily: "monospace",
            fontSize: 13, color: TEAL,
            letterSpacing: "0.3em",
            fontWeight: 700, textTransform: "uppercase",
          }}>
            Pipeline Processing {cursorOn ? "▌" : " "}
          </span>
        </div>
      </div>

      {/* Query bubble */}
      <div style={{ position: "absolute", top: 148, width: "100%", textAlign: "center", opacity: queryOp }}>
        <div style={{
          display: "inline-block",
          background: "#FFFFFF",
          border: `1.5px solid ${SKY}66`,
          borderRadius: 28,
          padding: "12px 32px",
          fontSize: 18, color: TEXT, fontWeight: 500,
          boxShadow: `0 4px 24px rgba(14,165,233,0.12), 0 2px 8px rgba(0,0,0,0.05)`,
        }}>
          <span style={{ color: MUTED, fontStyle: "italic", marginRight: 4 }}>User asks:</span>
          "What is our refund policy?"
        </div>
        <div style={{ marginTop: 14, fontSize: 22, color: MUTED, opacity: 0.7 }}>↓</div>
      </div>

      {/* Gray baseline connectors */}
      {NODES.slice(0, 3).map((node, i) => {
        const nextX = NODES[i + 1].x;
        const connW = nextX - node.x - NODE_R * 2;
        return (
          <div key={i} style={{
            position: "absolute",
            left: node.x + NODE_R, top: NODE_Y - 3,
            height: 6, width: connW,
            background: "#E2E8F0", borderRadius: 3,
          }} />
        );
      })}

      {/* Teal progress connectors */}
      {LINE_F.map((startF, i) => {
        const p    = lineP(startF);
        const maxW = NODES[i + 1].x - NODES[i].x - NODE_R * 2;
        const col  = NODES[i + 1].color;
        return (
          <div key={i} style={{
            position: "absolute",
            left: NODES[i].x + NODE_R, top: NODE_Y - 3,
            height: 6, width: maxW * p,
            background: `linear-gradient(90deg, ${NODES[i].color}, ${col})`,
            borderRadius: 3,
            boxShadow: `0 0 10px ${col}44`,
          }} />
        );
      })}

      {/* Timing badges on connectors */}
      {LINE_F.map((_startF, i) => {
        const midX = (NODES[i].x + NODE_R + NODES[i + 1].x - NODE_R) / 2;
        return (
          <div key={i} style={{
            position: "absolute",
            left: midX - 36, top: NODE_Y - 42,
            opacity: timingOp(i),
          }}>
            <div style={{
              background: "#FFFFFF",
              border: `1px solid ${NODES[i + 1].color}55`,
              borderRadius: 10,
              padding: "4px 12px",
              fontSize: 13, fontWeight: 700, color: NODES[i + 1].color,
              boxShadow: `0 2px 8px ${NODES[i + 1].color}18`,
              whiteSpace: "nowrap",
            }}>
              {NODES[i + 1].timing}
            </div>
          </div>
        );
      })}

      {/* Data packets with trails */}
      {LINE_F.map((startF, i) => (
        <DataPacket
          key={i}
          startX={NODES[i].x + NODE_R}
          endX={NODES[i + 1].x - NODE_R}
          y={NODE_Y}
          startFrame={startF}
          frame={frame}
          color={NODES[i + 1].color}
        />
      ))}

      {/* Pipeline nodes */}
      {NODES.map((node, i) => {
        const s      = nodeSpr[i];
        const active = frame >= STAGE_F[i];
        const opacity = interpolate(s, [0, 1], [0, 1]);
        const scale   = interpolate(s, [0, 1], [0.64, 1.0]);
        const glow    = active ? interpolate(s, [0, 1], [0, 36]) : 0;
        const rel     = Math.max(0, frame - STAGE_F[i]);

        const icons = [
          <RetrieveIcon active={active} />,
          <RankIcon active={active} rel={rel} />,
          <GenerateIcon active={active} rel={rel} />,
          <SpeakIcon active={active} rel={rel} />,
        ];

        return (
          <div key={i} style={{
            position: "absolute",
            left: node.x - NODE_R, top: NODE_Y - NODE_R,
            width: NODE_R * 2, height: NODE_R * 2,
            borderRadius: "50%",
            background: active ? "#FFFFFF" : "#F1F5F9",
            border: `2.5px solid ${active ? node.color : "#E2E8F0"}`,
            boxShadow: active
              ? `0 0 ${glow}px ${node.color}44, 0 0 ${glow * 2}px ${node.color}18, 0 8px 32px rgba(0,0,0,0.08)`
              : "0 2px 12px rgba(0,0,0,0.05)",
            display: "flex", alignItems: "center", justifyContent: "center",
            opacity, transform: `scale(${scale})`,
          }}>
            {icons[i]}
          </div>
        );
      })}

      {/* Ripple rings from Speak node */}
      <RippleRings
        cx={NODES[3].x} cy={NODE_Y} r={NODE_R}
        color={TEAL} frame={frame} startFrame={STAGE_F[3]}
      />

      {/* Node labels */}
      {NODES.map((node, i) => (
        <div key={i} style={{
          position: "absolute",
          left: node.x - 110, top: NODE_Y + NODE_R + 22,
          width: 220, textAlign: "center",
          opacity: interpolate(nodeSpr[i], [0, 1], [0, 1]),
        }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: frame >= STAGE_F[i] ? node.color : TEXT }}>
            {node.label}
          </div>
          <div style={{ fontSize: 13, color: SUB, marginTop: 5, letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 500 }}>
            {node.sub}
          </div>
        </div>
      ))}

      {/* Step numbers */}
      {NODES.map((node, i) => (
        <div key={i} style={{
          position: "absolute",
          left: node.x - 16, top: NODE_Y - NODE_R - 44,
          width: 32, textAlign: "center",
          opacity: interpolate(nodeSpr[i], [0, 1], [0, 1]),
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: "50%",
            background: frame >= STAGE_F[i] ? node.color : "#E2E8F0",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15, fontWeight: 800, color: frame >= STAGE_F[i] ? "#FFFFFF" : MUTED,
            boxShadow: frame >= STAGE_F[i] ? `0 4px 12px ${node.color}44` : "none",
          }}>
            {i + 1}
          </div>
        </div>
      ))}

      {/* Finale */}
      {frame >= 270 && (
        <div style={{
          position: "absolute", width: "100%", bottom: 72,
          textAlign: "center",
          opacity: underOp,
          transform: `translateY(${underTY}px)`,
        }}>
          <span style={{ fontSize: 80, fontWeight: 800, color: TEXT, letterSpacing: "-0.02em" }}>Under </span>
          <span style={{
            fontSize: 80, fontWeight: 800, letterSpacing: "-0.02em",
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            2 seconds.
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};