import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const BG   = "#06060A";
const TEAL = "#00B896";
const CFG  = { damping: 14, stiffness: 80 } as const;

const ANSWER =
  "Your returns are accepted within 30 days of purchase. Contact our support team with your order number — we'll process the refund within 2 business days.";

const NODE_R = 58;
const NODE_Y = 350;
const NODES = [
  { x: 380,  label: "Context",  sub: "Fragments in" },
  { x: 760,  label: "LLM",     sub: "Generation"   },
  { x: 1140, label: "TTS",     sub: "Synthesis"    },
  { x: 1520, label: "Speaker", sub: "Voice Out"    },
];

const NODE_ACT = [45, 98, 155, 212];
const LINE_F   = [70, 124, 182];

const STRIP = { x: 220, y: 560, w: 1480, h: 185 };

// Drifting particles
function Particles({ frame }: { frame: number }) {
  const pts = Array.from({ length: 44 }, (_, i) => {
    const x    = (i * 137.5) % 100;
    const y    = (((i * 97.3) % 100) + frame * (0.01 + (i % 7) * 0.003)) % 100;
    const size = 0.8 + (i % 4) * 0.55;
    const op   = 0.04 + (i % 5) * 0.018;
    return { x, y, size, op };
  });
  return (
    <>
      {pts.map((p, i) => (
        <div key={i} style={{
          position: "absolute", left: `${p.x}%`, top: `${p.y}%`,
          width: p.size, height: p.size, borderRadius: "50%",
          background: TEAL, opacity: p.op, pointerEvents: "none",
        }} />
      ))}
    </>
  );
}

// Moving data packet along connector
function DataPacket({ startX, endX, y, startFrame, frame }: {
  startX: number; endX: number; y: number; startFrame: number; frame: number;
}) {
  const p = interpolate(frame, [startFrame, startFrame + 28], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  if (p <= 0 || p >= 1) return null;
  const x  = interpolate(p, [0, 1], [startX, endX]);
  const op = p < 0.1 ? p * 10 : p > 0.9 ? (1 - p) * 10 : 1;
  return (
    <div style={{
      position: "absolute",
      left: x - 5, top: y - 5,
      width: 10, height: 10, borderRadius: "50%",
      background: TEAL,
      boxShadow: `0 0 14px ${TEAL}, 0 0 28px ${TEAL}88`,
      opacity: op, pointerEvents: "none",
    }} />
  );
}

const NodeIcon: React.FC<{ idx: number; active: boolean; rel: number }> = ({ idx, active, rel }) => {
  const c = active ? TEAL : "#1E2030";

  if (idx === 0) {
    return (
      <div style={{ display: "flex", gap: 4 }}>
        {[36, 48, 30].map((h, i) => (
          <div key={i} style={{
            width: 7, height: h, background: c, borderRadius: 3,
            boxShadow: active ? `0 0 8px ${TEAL}88` : "none",
          }} />
        ))}
      </div>
    );
  }
  if (idx === 1) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 5, padding: "2px 4px" }}>
        {[70, 50, 62].map((w, i) => (
          <div key={i} style={{
            height: 4, width: `${w}%`,
            background: c, borderRadius: 2,
            opacity: active
              ? interpolate(rel, [i * 12, i * 12 + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
              : 0.2,
            boxShadow: active ? `0 0 6px ${TEAL}66` : "none",
          }} />
        ))}
      </div>
    );
  }
  if (idx === 2) {
    return (
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        {[0, 1, 2, 3].map((i) => {
          const h = active ? 10 + Math.abs(Math.sin(((rel + i * 8) / 24) * Math.PI)) * 30 : 8;
          return (
            <div key={i} style={{
              width: 6, height: h, background: c, borderRadius: 3,
              boxShadow: active ? `0 0 8px ${TEAL}88` : "none",
            }} />
          );
        })}
      </div>
    );
  }
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {[0, 1, 2, 3, 4].map((i) => {
        const h = active ? 8 + Math.abs(Math.sin(((rel + i * 9) / 28) * Math.PI)) * 38 : 8;
        return (
          <div key={i} style={{
            width: 6, height: h, background: c, borderRadius: 3,
            boxShadow: active ? `0 0 8px ${TEAL}88` : "none",
          }} />
        );
      })}
    </div>
  );
};

export const GenerateAndSpeak: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const spr = (startF: number) =>
    spring({ frame: Math.max(0, frame - startF), fps, config: CFG, durationInFrames: 30 });

  const nodeSpr = NODE_ACT.map((f) => spr(f));

  const headerOpacity = interpolate(frame, [0, 22], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const lineP = (startF: number) =>
    interpolate(frame, [startF, startF + 26], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });

  // Answer streams in (160-218)
  const charCount = Math.floor(interpolate(
    frame, [160, 220], [0, ANSWER.length],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  ));

  // Strip fade (155-172)
  const stripOpacity = interpolate(frame, [152, 172], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const stripSpr = spring({ frame: Math.max(0, frame - 152), fps, config: CFG, durationInFrames: 28 });
  const stripTY  = interpolate(stripSpr, [0, 1], [18, 0]);

  const cursorVisible = frame >= 160 && frame < 222 && Math.floor(frame / 8) % 2 === 0;

  const speakerX = NODES[3].x;
  const waveRel  = Math.max(0, frame - 218);

  // Finale (276+)
  const underSpr = spring({ frame: Math.max(0, frame - 276), fps, config: CFG, durationInFrames: 30 });
  const underOp  = interpolate(underSpr, [0, 1], [0, 1]);
  const underTY  = interpolate(underSpr, [0, 1], [28, 0]);

  const cursorOn = Math.floor(frame / 14) % 2 === 0;

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: "sans-serif" }}>
      <Particles frame={frame} />

      {/* Header */}
      <div style={{
        position: "absolute", top: 66, width: "100%",
        textAlign: "center", opacity: headerOpacity,
      }}>
        <span style={{
          fontFamily: "monospace",
          fontSize: 11, color: TEAL,
          letterSpacing: "0.32em",
          fontWeight: 700, textTransform: "uppercase",
        }}>
          Generate &amp; Speak {cursorOn ? "▌" : " "}
        </span>
      </div>

      {/* Gray baseline connectors */}
      {NODES.slice(0, 3).map((n, i) => {
        const nx = NODES[i + 1].x;
        return (
          <div key={i} style={{
            position: "absolute",
            left: n.x + NODE_R, top: NODE_Y - 2,
            height: 4, width: nx - n.x - NODE_R * 2,
            background: "#1A1A28", borderRadius: 2,
          }} />
        );
      })}

      {/* Teal progress connectors */}
      {LINE_F.map((startF, i) => {
        const p    = lineP(startF);
        const maxW = NODES[i + 1].x - NODES[i].x - NODE_R * 2;
        return (
          <div key={i} style={{
            position: "absolute",
            left: NODES[i].x + NODE_R, top: NODE_Y - 2,
            height: 4, width: maxW * p,
            background: `linear-gradient(90deg, ${TEAL}88, ${TEAL})`,
            borderRadius: 2,
            boxShadow: `0 0 8px ${TEAL}66`,
          }} />
        );
      })}

      {/* Data packets */}
      {LINE_F.map((startF, i) => (
        <DataPacket
          key={i}
          startX={NODES[i].x + NODE_R}
          endX={NODES[i + 1].x - NODE_R}
          y={NODE_Y}
          startFrame={startF}
          frame={frame}
        />
      ))}

      {/* Nodes */}
      {NODES.map((node, i) => {
        const s      = nodeSpr[i];
        const active = frame >= NODE_ACT[i];
        const opacity = interpolate(s, [0, 1], [0, 1]);
        const scale   = interpolate(s, [0, 1], [0.70, 1.0]);
        const glow    = active ? interpolate(s, [0, 1], [0, 28]) : 0;
        const rel     = Math.max(0, frame - NODE_ACT[i]);

        return (
          <div key={i} style={{
            position: "absolute",
            left: node.x - NODE_R, top: NODE_Y - NODE_R,
            width: NODE_R * 2, height: NODE_R * 2,
            borderRadius: "50%",
            background: active ? "#0E0E18" : "#0A0A12",
            border: `2px solid ${active ? TEAL : "#1E2030"}`,
            boxShadow: active ? `0 0 ${glow}px ${TEAL}66, 0 0 ${glow * 2}px ${TEAL}22` : "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            opacity, transform: `scale(${scale})`,
          }}>
            <NodeIcon idx={i} active={active} rel={rel} />
          </div>
        );
      })}

      {/* Node labels */}
      {NODES.map((node, i) => (
        <div key={i} style={{
          position: "absolute",
          left: node.x - 60, top: NODE_Y + NODE_R + 16,
          width: 120, textAlign: "center",
          opacity: interpolate(nodeSpr[i], [0, 1], [0, 1]),
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#FFFFFF" }}>{node.label}</div>
          <div style={{ fontSize: 9, color: "#4A5270", marginTop: 3, letterSpacing: "0.08em", textTransform: "uppercase" }}>{node.sub}</div>
        </div>
      ))}

      {/* Answer text strip */}
      {frame >= 150 && (
        <div style={{
          position: "absolute",
          left: STRIP.x, top: STRIP.y,
          width: STRIP.w, height: STRIP.h,
          background: "#0A0A14",
          border: "1px solid rgba(255,255,255,0.06)",
          borderLeft: `4px solid ${TEAL}`,
          borderRadius: "0 12px 12px 0",
          boxShadow: `0 0 40px rgba(0,0,0,0.6), 0 0 0 1px ${TEAL}22`,
          padding: "22px 28px",
          opacity: stripOpacity,
          transform: `translateY(${stripTY}px)`,
          display: "flex", flexDirection: "column", justifyContent: "center",
        }}>
          <div style={{ fontSize: 9, color: TEAL, fontWeight: 700, letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: 14, opacity: 0.8 }}>
            Answer
          </div>
          <div style={{ fontSize: 18, color: "#D0D8F0", lineHeight: 1.7, fontWeight: 400 }}>
            {ANSWER.slice(0, charCount)}
            {cursorVisible && <span style={{ color: TEAL, fontWeight: 700 }}>|</span>}
          </div>
        </div>
      )}

      {/* Sound wave ripples from Speaker node */}
      {frame >= 218 && [0, 20, 40].map((offset, i) => {
        const t = ((waveRel + offset) % 60) / 60;
        const r = NODE_R + t * 96;
        return (
          <div key={i} style={{
            position: "absolute",
            left: speakerX - r, top: NODE_Y - r,
            width: r * 2, height: r * 2,
            borderRadius: "50%",
            border: `1.5px solid ${TEAL}`,
            opacity: (1 - t) * 0.5,
            pointerEvents: "none",
          }} />
        );
      })}

      {/* Finale */}
      {frame >= 274 && (
        <div style={{
          position: "absolute",
          width: "100%", bottom: 60,
          textAlign: "center",
          opacity: underOp,
          transform: `translateY(${underTY}px)`,
        }}>
          <span style={{ fontSize: 68, fontWeight: 800, color: "#FFFFFF", letterSpacing: "-0.02em" }}>Under </span>
          <span style={{
            fontSize: 68, fontWeight: 800, color: TEAL, letterSpacing: "-0.02em",
            textShadow: `0 0 40px ${TEAL}88`,
          }}>
            2 seconds.
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
