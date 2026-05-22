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
const AMBER = "#D97706";
const TEXT  = "#0F172A";
const SUB   = "#64748B";
const MUTED = "#94A3B8";
const CFG   = { damping: 14, stiffness: 80 } as const;

// ── Layout ────────────────────────────────────────────────────────────────────
const VAULT = { cx: 240, cy: 540, w: 200, h: 260 };
const DS    = { cx: 1700, cy: 540, r: 108 };

const FC_X = 580;
const FC_W = 600;
const FC_H = 140;
const FC_Y = [350, 500, 650];

const FRAGMENTS = [
  { title: "Return Policy — Section 3.2",   excerpt: "Customers may request a refund within 30 days of purchase provided the item is unused and in original packaging.",   match: 96, color: "#D97706", startF: 120 },
  { title: "Customer Service Guidelines",    excerpt: "All refund requests must be submitted through the official support portal with the original order number attached.",    match: 91, color: "#0EA5E9", startF: 164 },
  { title: "Refund Processing Steps",        excerpt: "Once approved, refunds are processed within 2–5 business days back to the original payment method used at checkout.",  match: 87, color: "#8B5CF6", startF: 208 },
];

// ── Vault node ────────────────────────────────────────────────────────────────
const VaultNode: React.FC<{ frame: number; searching: boolean }> = ({ frame, searching }) => {
  const glowPulse  = 0.5 + 0.5 * Math.sin((frame / 24) * Math.PI * 2);
  const glowSpread = searching ? interpolate(glowPulse, [0, 1], [18, 42]) : 16;

  // Scan line inside vault
  const scanY = searching ? ((frame * 4) % (VAULT.h - 20)) : -10;

  return (
    <div style={{
      position: "absolute",
      left: VAULT.cx - VAULT.w / 2, top: VAULT.cy - VAULT.h / 2,
      width: VAULT.w, height: VAULT.h,
      background: "#FFFFFF",
      border: `2px solid ${TEAL}`,
      borderRadius: 18,
      boxShadow: `0 0 ${glowSpread}px rgba(13,148,136,0.2), 0 0 ${glowSpread * 2}px rgba(13,148,136,0.08), 0 8px 28px rgba(0,0,0,0.07)`,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 12, overflow: "hidden",
    }}>
      {/* Scan line */}
      {searching && (
        <div style={{
          position: "absolute", left: 0, top: scanY,
          width: "100%", height: 3,
          background: `linear-gradient(90deg, transparent, ${SKY}88, ${TEAL}66, transparent)`,
          pointerEvents: "none",
        }} />
      )}

      {/* Stacked documents */}
      <div style={{ position: "relative", width: 70, height: 82 }}>
        {[2, 1, 0].map((i) => (
          <div key={i} style={{
            position: "absolute",
            left: i * 7, top: i * 7,
            width: 56, height: 68,
            background: i === 0 ? `${TEAL}12` : "#F8FAFC",
            border: `1.5px solid ${i === 0 ? TEAL : "#E2E8F0"}`,
            borderRadius: 7,
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", gap: 4, padding: 8,
          }}>
            {i === 0 && (
              <>
                {[80, 60, 72, 50].map((w, j) => (
                  <div key={j} style={{
                    width: `${w}%`, height: 3,
                    background: `linear-gradient(90deg, ${SKY}, ${TEAL})`, borderRadius: 1,
                  }} />
                ))}
              </>
            )}
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, fontWeight: 700, color: TEAL, letterSpacing: "0.12em", textTransform: "uppercase" }}>
        Knowledge
      </div>
      <div style={{ fontSize: 11, fontWeight: 700, color: TEAL, letterSpacing: "0.12em", textTransform: "uppercase", marginTop: -10 }}>
        Base
      </div>
    </div>
  );
};

// ── DeepSeek node ─────────────────────────────────────────────────────────────
const DeepSeekNode: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  const DS_START = 248;
  const spr     = spring({ frame: Math.max(0, frame - DS_START), fps, config: CFG, durationInFrames: 40 });
  const opacity = interpolate(spr, [0, 1], [0, 1]);
  const scale   = interpolate(spr, [0, 1], [0.64, 1.0]);
  const glow    = interpolate(spr, [0, 1], [0, 36]);
  const rel     = Math.max(0, frame - DS_START);
  const barH    = (i: number) => 14 + Math.abs(Math.sin(((rel + i * 10) / 26) * Math.PI)) * 36;

  return (
    <div style={{
      position: "absolute",
      left: DS.cx - DS.r, top: DS.cy - DS.r,
      width: DS.r * 2, height: DS.r * 2,
      borderRadius: "50%",
      background: "#FFFFFF",
      border: `2.5px solid ${TEAL}`,
      boxShadow: `0 0 ${glow}px rgba(13,148,136,0.22), 0 0 ${glow * 2}px rgba(13,148,136,0.08), 0 8px 32px rgba(0,0,0,0.08)`,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 10, opacity, transform: `scale(${scale})`,
    }}>
      {/* AI bars icon */}
      <div style={{ display: "flex", gap: 6, alignItems: "flex-end" }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{
            width: 8, height: barH(i), borderRadius: 4,
            background: `linear-gradient(to top, ${SKY}, ${TEAL})`,
            boxShadow: `0 0 8px ${TEAL}55`,
          }} />
        ))}
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: TEXT }}>DeepSeek</div>
        <div style={{ fontSize: 11, color: SUB, fontWeight: 500, letterSpacing: "0.06em" }}>AI · LLM</div>
      </div>
    </div>
  );
};

// ── Fragment card ─────────────────────────────────────────────────────────────
const FragmentCard: React.FC<{
  frag: typeof FRAGMENTS[0]; idx: number; frame: number; fps: number;
}> = ({ frag, idx, frame, fps }) => {
  const spr     = spring({ frame: Math.max(0, frame - frag.startF), fps, config: CFG, durationInFrames: 30 });
  const opacity = interpolate(spr, [0, 1], [0, 1]);
  const tx      = interpolate(spr, [0, 1], [VAULT.cx + VAULT.w / 2 + 20, FC_X]);

  const badgeSpr = spring({ frame: Math.max(0, frame - (frag.startF + 16)), fps, config: CFG, durationInFrames: 20 });
  const badgeOp  = interpolate(badgeSpr, [0, 1], [0, 1]);
  const badgeSc  = interpolate(badgeSpr, [0, 1], [0.7, 1.0]);

  return (
    <div style={{
      position: "absolute",
      left: tx, top: FC_Y[idx],
      width: FC_W, height: FC_H,
      opacity,
      background: "#FFFFFF",
      borderLeft: `5px solid ${frag.color}`,
      borderTop: "1.5px solid #E2E8F0",
      borderRight: "1.5px solid #E2E8F0",
      borderBottom: "1.5px solid #E2E8F0",
      borderRadius: "0 14px 14px 0",
      boxShadow: `0 4px 20px ${frag.color}12, 0 2px 8px rgba(0,0,0,0.05)`,
      padding: "14px 18px",
      display: "flex", flexDirection: "column", justifyContent: "space-between",
    }}>
      {/* Title + match badge */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: TEXT, lineHeight: 1.3, flex: 1 }}>
          {frag.title}
        </div>
        <div style={{
          fontSize: 13, fontWeight: 800, color: frag.color,
          background: `${frag.color}14`,
          border: `1.5px solid ${frag.color}44`,
          borderRadius: 20,
          padding: "4px 12px",
          opacity: badgeOp,
          transform: `scale(${badgeSc})`,
          flexShrink: 0,
          whiteSpace: "nowrap",
        }}>
          {frag.match}% match
        </div>
      </div>

      {/* Text excerpt */}
      <div style={{
        fontSize: 13, color: SUB, lineHeight: 1.6,
        overflow: "hidden",
        display: "-webkit-box",
        WebkitLineClamp: 2,
        WebkitBoxOrient: "vertical",
      }}>
        {frag.excerpt}
      </div>

      {/* Match score bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ flex: 1, height: 5, background: "#F1F5F9", borderRadius: 2.5 }}>
          <div style={{
            height: "100%", width: `${frag.match}%`,
            background: `linear-gradient(90deg, ${frag.color}88, ${frag.color})`,
            borderRadius: 2.5,
          }} />
        </div>
        <span style={{ fontSize: 11, color: MUTED, fontWeight: 600, whiteSpace: "nowrap" }}>
          Semantic score
        </span>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const SearchRetrieval: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const vaultSpr     = spring({ frame, fps, config: CFG, durationInFrames: 50 });
  const vaultOpacity = interpolate(vaultSpr, [0, 1], [0, 1]);

  const queryOp = interpolate(frame, [0, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const arrowP  = interpolate(frame, [32, 62], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const searching = frame >= 88 && frame < FRAGMENTS[2].startF + 22;

  const vaultToFrag = FRAGMENTS.map((f, i) => ({
    visible: frame >= f.startF,
    x1: VAULT.cx + VAULT.w / 2,
    y1: VAULT.cy,
    x2: FC_X,
    y2: FC_Y[i] + FC_H / 2,
  }));

  const fragToDS = FRAGMENTS.map((f, i) => ({
    visible: frame >= 226 + i * 14,
    x1: FC_X + FC_W,
    y1: FC_Y[i] + FC_H / 2,
    x2: DS.cx - DS.r,
    y2: DS.cy,
  }));

  const resultSpr = spring({ frame: Math.max(0, frame - 278), fps, config: CFG, durationInFrames: 30 });
  const resultOp  = interpolate(resultSpr, [0, 1], [0, 1]);
  const resultTY  = interpolate(resultSpr, [0, 1], [24, 0]);

  const QUERY_Y  = 104;
  const ARROW_Y2 = VAULT.cy - VAULT.h / 2;

  // Semantic pulse rings from vault during search
  const pulseRings = searching
    ? [0, 18, 36].map((offset) => {
      const t = ((frame + offset) % 48) / 48;
      return { r: (VAULT.w / 2 + 10) + t * 120, op: (1 - t) * 0.2 };
    })
    : [];

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 120% 80% at 15% 50%, rgba(14,165,233,0.05) 0%, #F8FAFF 55%)",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      {/* SVG lines layer */}
      <svg
        style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", overflow: "visible", pointerEvents: "none" }}
        viewBox="0 0 1920 1080"
      >
        {/* Semantic search pulse rings */}
        {pulseRings.map((ring, i) => (
          <ellipse
            key={i}
            cx={VAULT.cx} cy={VAULT.cy}
            rx={ring.r} ry={ring.r * 0.55}
            fill="none"
            stroke={TEAL}
            strokeWidth="1.5"
            opacity={ring.op}
          />
        ))}

        {/* Query → vault arrow */}
        {arrowP > 0 && (
          <line
            x1={VAULT.cx} y1={QUERY_Y + 36}
            x2={VAULT.cx} y2={QUERY_Y + 36 + (ARROW_Y2 - QUERY_Y - 36) * arrowP}
            stroke={SKY} strokeWidth="2.5" strokeDasharray="8 6" opacity={0.8}
          />
        )}

        {/* Vault → fragment lines */}
        {vaultToFrag.map((l, i) =>
          l.visible ? (
            <line key={`vf${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
              stroke={FRAGMENTS[i].color} strokeWidth="2" strokeDasharray="9 7" opacity={0.5}
            />
          ) : null
        )}

        {/* Midpoint dots on vault→frag lines */}
        {vaultToFrag.map((l, i) =>
          l.visible ? (
            <circle key={`dot${i}`} cx={(l.x1 + l.x2) / 2} cy={(l.y1 + l.y2) / 2}
              r={5} fill={FRAGMENTS[i].color} opacity={0.6}
            />
          ) : null
        )}

        {/* Fragment → DeepSeek lines */}
        {fragToDS.map((l, i) =>
          l.visible ? (
            <line key={`fd${i}`} x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
              stroke={TEAL} strokeWidth="2" strokeDasharray="9 7" opacity={0.5}
            />
          ) : null
        )}
      </svg>

      {/* Query bubble */}
      <div style={{
        position: "absolute",
        left: VAULT.cx - 150, top: QUERY_Y - 22,
        opacity: queryOp,
      }}>
        <div style={{
          background: "#FFFFFF",
          border: `1.5px solid ${SKY}66`,
          borderRadius: 24,
          padding: "10px 22px",
          fontSize: 15, color: TEXT, fontWeight: 500,
          boxShadow: `0 4px 20px rgba(14,165,233,0.12), 0 2px 6px rgba(0,0,0,0.05)`,
          whiteSpace: "nowrap",
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <circle cx="10" cy="10" r="6" stroke={SKY} strokeWidth="2" />
            <line x1="14.5" y1="14.5" x2="20" y2="20" stroke={SKY} strokeWidth="2" strokeLinecap="round" />
          </svg>
          "What is our refund policy?"
        </div>
      </div>

      {/* Vault */}
      <div style={{ opacity: vaultOpacity }}>
        <VaultNode frame={frame} searching={searching} />
      </div>
      <div style={{
        position: "absolute",
        left: VAULT.cx - 70, top: VAULT.cy + VAULT.h / 2 + 16,
        width: 140, textAlign: "center",
        opacity: vaultOpacity,
        fontSize: 12, color: SUB,
        letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600,
      }}>
        Knowledge Base
      </div>

      {/* Fragment cards */}
      {FRAGMENTS.map((frag, i) => (
        frame >= frag.startF - 2 && (
          <FragmentCard key={i} frag={frag} idx={i} frame={frame} fps={fps} />
        )
      ))}

      {/* Fragment section label */}
      {frame >= FRAGMENTS[0].startF && (
        <div style={{
          position: "absolute",
          left: FC_X, top: FC_Y[2] + FC_H + 18,
          width: FC_W, textAlign: "center",
          fontSize: 13, color: MUTED,
          letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600,
          opacity: interpolate(frame, [FRAGMENTS[2].startF + 22, FRAGMENTS[2].startF + 40], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          }),
        }}>
          Top-3 semantic matches · Retrieved via FAISS
        </div>
      )}

      {/* DeepSeek node */}
      <DeepSeekNode frame={frame} fps={fps} />
      <div style={{
        position: "absolute",
        left: DS.cx - 80, top: DS.cy + DS.r + 18,
        width: 160, textAlign: "center",
        fontSize: 13, color: SUB,
        letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 600,
        opacity: interpolate(frame, [248, 268], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}>
        LLM Synthesis
      </div>

      {/* Result */}
      {frame >= 276 && (
        <div style={{
          position: "absolute", width: "100%", bottom: 72,
          textAlign: "center",
          opacity: resultOp,
          transform: `translateY(${resultTY}px)`,
        }}>
          <span style={{ fontSize: 68, fontWeight: 800, color: TEXT, letterSpacing: "-0.02em" }}>
            Relevant context found in{" "}
          </span>
          <span style={{
            fontSize: 68, fontWeight: 800, letterSpacing: "-0.02em",
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            milliseconds.
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};