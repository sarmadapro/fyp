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
const GREEN = "#059669";
const CFG   = { damping: 14, stiffness: 80 } as const;

const PANEL = { x: 200, y: 100, w: 1520, h: 880 };
const UPL   = { x: 240,  y: 220, w: 620, h: 700 };
const VLT   = { x: 980,  y: 220, w: 580, h: 700 };

const FILES = [
  { name: "Annual_Report_2024.pdf",         size: "2.4 MB", pages: "48 pages",  color: "#EF4444", start: 55,  prog: [75,  115] },
  { name: "Product_Catalogue.pdf",          size: "1.8 MB", pages: "32 pages",  color: "#F59E0B", start: 120, prog: [138, 175] },
  { name: "Namal_University_Overview.pdf",  size: "3.1 MB", pages: "64 pages",  color: "#8B5CF6", start: 178, prog: [196, 235] },
];

// ── PDF icon with color accent ────────────────────────────────────────────────
const PdfIcon: React.FC<{ done: boolean; color: string }> = ({ done, color }) => (
  <div style={{
    width: 48, height: 60, flexShrink: 0,
    background: done ? `${color}14` : "#FEF2F2",
    border: `1.5px solid ${done ? color : `${color}66`}`,
    borderRadius: 8,
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 3,
    position: "relative",
  }}>
    {/* Dog-ear */}
    <div style={{
      position: "absolute", right: 0, top: 0,
      width: 0, height: 0,
      borderLeft: "12px solid transparent",
      borderTop: `12px solid ${done ? color : `${color}99`}`,
    }} />
    <span style={{ fontSize: 9, fontWeight: 800, color: done ? color : `${color}BB`, letterSpacing: "0.04em" }}>PDF</span>
    <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "0 6px" }}>
      {[80, 60, 70].map((w, i) => (
        <div key={i} style={{ height: 2.5, width: `${w}%`, background: done ? color : `${color}66`, borderRadius: 1 }} />
      ))}
    </div>
  </div>
);

// ── Animated check circle ─────────────────────────────────────────────────────
const CheckCircle: React.FC<{ color: string }> = ({ color }) => (
  <div style={{
    width: 26, height: 26, borderRadius: "50%",
    background: color,
    boxShadow: `0 0 12px ${color}66, 0 4px 8px ${color}33`,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  }}>
    <svg width="13" height="13" viewBox="0 0 12 12">
      <polyline points="2,6 5,9 10,3" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </div>
);

// ── File upload card ──────────────────────────────────────────────────────────
const FileCard: React.FC<{ file: typeof FILES[0]; frame: number; fps: number }> = ({ file, frame, fps }) => {
  const enterSpr = spring({ frame: Math.max(0, frame - file.start), fps, config: CFG, durationInFrames: 28 });
  const cardOp   = interpolate(enterSpr, [0, 1], [0, 1]);
  const cardY    = interpolate(enterSpr, [0, 1], [-20, 0]);

  const progress = interpolate(frame, [file.prog[0], file.prog[1]], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const done = frame >= file.prog[1] + 6;
  const pct  = Math.round(progress * 100);

  return (
    <div style={{
      opacity: cardOp,
      transform: `translateY(${cardY}px)`,
      background: "#FFFFFF",
      border: `1.5px solid ${done ? `${file.color}44` : "#E2E8F0"}`,
      borderRadius: 14,
      padding: "16px 18px",
      boxShadow: done
        ? `0 4px 20px ${file.color}14, 0 1px 4px rgba(0,0,0,0.05)`
        : "0 2px 12px rgba(0,0,0,0.05)",
      marginBottom: 14,
    }}>
      {/* File info row */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
        <PdfIcon done={done} color={file.color} />
        <div style={{ flex: 1, overflow: "hidden" }}>
          <div style={{
            fontSize: 14, fontWeight: 600, color: TEXT,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            marginBottom: 4,
          }}>
            {file.name}
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <span style={{ fontSize: 12, color: SUB }}>{file.size}</span>
            <span style={{ fontSize: 12, color: MUTED }}>·</span>
            <span style={{ fontSize: 12, color: SUB }}>{file.pages}</span>
          </div>
        </div>
        {done
          ? <CheckCircle color={file.color} />
          : progress > 0 && (
            <span style={{ fontSize: 13, fontWeight: 700, color: file.color, flexShrink: 0 }}>{pct}%</span>
          )
        }
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: "#F1F5F9", borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          width: `${progress * 100}%`,
          background: done
            ? `linear-gradient(90deg, ${file.color}, ${file.color}BB)`
            : `linear-gradient(90deg, ${SKY}, ${file.color})`,
          borderRadius: 3,
          boxShadow: progress > 0.1 ? `0 0 8px ${file.color}55` : "none",
          transition: "none",
        }} />
      </div>

      {done && (
        <div style={{ marginTop: 8, fontSize: 12, color: file.color, fontWeight: 600, letterSpacing: "0.03em" }}>
          ✓ Indexed into Knowledge Base
        </div>
      )}
    </div>
  );
};

// ── Knowledge Vault ───────────────────────────────────────────────────────────
const Vault: React.FC<{ frame: number; fps: number; docsIndexed: number }> = ({ frame, fps, docsIndexed }) => {
  const glowPulse  = 0.5 + 0.5 * Math.sin((frame / 40) * Math.PI * 2);
  const glowSpread = interpolate(glowPulse, [0, 1], [20, 50]);

  const countSpr = spring({ frame: Math.max(0, frame - 240), fps, config: CFG, durationInFrames: 32 });
  const countOp  = interpolate(countSpr, [0, 1], [0, 1]);
  const countSc  = interpolate(countSpr, [0, 1], [0.75, 1.0]);

  // Scan line animation inside vault
  const scanY = frame >= 80
    ? (((frame - 80) * 3) % 160)
    : -20;
  const scanOp = docsIndexed > 0 && docsIndexed < 3 ? 0.6 : 0;

  // Floating vector dots (appear as documents index)
  const vectorDots = Array.from({ length: 18 }, (_, i) => {
    const angle = (i / 18) * Math.PI * 2 + frame * 0.018;
    const r = 68 + (i % 3) * 18;
    const x = Math.cos(angle) * r;
    const y = Math.sin(angle) * r * 0.6;
    const visible = docsIndexed > i / 6;
    return { x, y, visible, col: [SKY, TEAL, "#8B5CF6"][i % 3] };
  });

  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 28,
    }}>
      {/* Vault container */}
      <div style={{
        position: "relative",
        width: 280, height: 280,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {/* Orbit ring */}
        <div style={{
          position: "absolute",
          width: 260, height: 156,
          borderRadius: "50%",
          border: `1px dashed ${TEAL}44`,
        }} />

        {/* Vector orbit dots */}
        {vectorDots.map((d, i) => d.visible && (
          <div key={i} style={{
            position: "absolute",
            left: 140 + d.x - 5,
            top: 140 + d.y - 5,
            width: 10, height: 10,
            borderRadius: "50%",
            background: d.col,
            boxShadow: `0 0 8px ${d.col}88`,
            opacity: 0.7,
          }} />
        ))}

        {/* Main vault box */}
        <div style={{
          width: 180, height: 180,
          background: "#FFFFFF",
          border: `2px solid ${TEAL}`,
          borderRadius: 24,
          boxShadow: `0 0 ${glowSpread}px rgba(13,148,136,0.2), 0 0 ${glowSpread * 2}px rgba(13,148,136,0.08), 0 8px 32px rgba(0,0,0,0.08)`,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          gap: 14, overflow: "hidden", position: "relative",
        }}>
          {/* Scan line */}
          <div style={{
            position: "absolute", left: 0, top: scanY,
            width: "100%", height: 3,
            background: `linear-gradient(90deg, transparent, ${SKY}88, ${TEAL}88, transparent)`,
            opacity: scanOp, pointerEvents: "none",
          }} />

          {/* Stacked document icons */}
          <div style={{ position: "relative", width: 80, height: 92 }}>
            {[2, 1, 0].map((i) => (
              <div key={i} style={{
                position: "absolute",
                left: i * 8, top: i * 8,
                width: 64, height: 76,
                background: i === 0 ? `${TEAL}14` : "#F8FAFC",
                border: `1.5px solid ${i === 0 ? TEAL : "#E2E8F0"}`,
                borderRadius: 8,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {i === 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 5, padding: 10 }}>
                    {[80, 60, 72].map((w, j) => (
                      <div key={j} style={{
                        width: `${w}%`, height: 4,
                        background: `linear-gradient(90deg, ${SKY}, ${TEAL})`, borderRadius: 2,
                      }} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: TEAL, letterSpacing: "0.12em", textTransform: "uppercase" }}>
            Knowledge Base
          </div>
        </div>
      </div>

      {/* Doc count */}
      {docsIndexed > 0 && (
        <div style={{ textAlign: "center", opacity: countOp, transform: `scale(${countSc})` }}>
          <div style={{
            fontSize: 64, fontWeight: 800,
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            letterSpacing: "-0.03em", lineHeight: 1,
          }}>
            {docsIndexed}
          </div>
          <div style={{ fontSize: 14, color: SUB, marginTop: 8, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600 }}>
            {docsIndexed === 1 ? "document" : "documents"} indexed
          </div>
          {/* Embedding stats */}
          <div style={{ marginTop: 12, display: "flex", gap: 16, justifyContent: "center" }}>
            {["384 dims", "FAISS Index", "Ready"].map((label, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 5,
              }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: [SKY, TEAL, GREEN][i] }} />
                <span style={{ fontSize: 12, color: SUB, fontWeight: 500 }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const UploadFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const panelSpr   = spring({ frame, fps, config: CFG, durationInFrames: 46 });
  const panelOp    = interpolate(panelSpr, [0, 1], [0, 1]);
  const panelScale = interpolate(panelSpr, [0, 1], [0.96, 1.0]);

  const zonePulse    = frame < 55 ? 0.5 + 0.5 * Math.sin((frame / 20) * Math.PI * 2) : 1;
  const zoneBorderOp = interpolate(zonePulse, [0, 1], [0.35, 1.0]);

  const labelOp = interpolate(frame, [228, 245], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const vaultSpr   = spring({ frame: Math.max(0, frame - 230), fps, config: CFG, durationInFrames: 42 });
  const vaultOp    = interpolate(vaultSpr, [0, 1], [0, 1]);
  const vaultScale = interpolate(vaultSpr, [0, 1], [0.84, 1.0]);

  const allDone      = frame >= FILES[2].prog[1] + 6;
  const docsIndexed  = FILES.filter(f => frame >= f.prog[1] + 6).length;
  const divPulse     = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin((frame / 28) * Math.PI * 2));

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse 120% 80% at 50% -20%, rgba(14,165,233,0.06) 0%, #F8FAFF 50%)",
      fontFamily: "'Inter', 'Segoe UI', sans-serif",
    }}>
      {/* Main panel */}
      <div style={{
        position: "absolute",
        left: PANEL.x, top: PANEL.y,
        width: PANEL.w, height: PANEL.h,
        background: "#FFFFFF",
        border: "1.5px solid #E2E8F0",
        borderRadius: 20,
        boxShadow: "0 8px 48px rgba(13,148,136,0.08), 0 2px 12px rgba(0,0,0,0.05)",
        opacity: panelOp,
        transform: `scale(${panelScale})`,
        overflow: "hidden",
      }}>
        {/* Panel header */}
        <div style={{
          height: 64,
          borderBottom: "1.5px solid #E2E8F0",
          background: "linear-gradient(90deg, #F8FAFF, #FFFFFF)",
          display: "flex",
          alignItems: "center",
          padding: "0 28px",
          gap: 14,
        }}>
          {/* Icon */}
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, ${SKY}, ${TEAL})`,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            boxShadow: `0 4px 12px ${TEAL}33`,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <polyline points="14,2 14,8 20,8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, color: TEXT }}>Document Upload</div>
            <div style={{ fontSize: 12, color: SUB }}>VoiceRAG Knowledge Base</div>
          </div>
          {allDone && (
            <div style={{
              marginLeft: "auto",
              fontSize: 13, color: GREEN,
              background: "#ECFDF5",
              border: "1px solid #A7F3D0",
              borderRadius: 20,
              padding: "6px 16px",
              opacity: labelOp,
              fontWeight: 700,
              display: "flex", alignItems: "center", gap: 6,
            }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: GREEN, boxShadow: `0 0 6px ${GREEN}` }} />
              3 documents indexed · Ready
            </div>
          )}
        </div>

        {/* Upload section */}
        <div style={{
          position: "absolute",
          left: UPL.x - PANEL.x, top: UPL.y - PANEL.y,
          width: UPL.w, height: UPL.h,
          padding: "4px 0",
        }}>
          {/* Upload zone */}
          {frame < FILES[0].start && (
            <div style={{
              width: "100%", height: 110,
              border: `2.5px dashed ${TEAL}`,
              borderRadius: 14,
              background: `${TEAL}06`,
              opacity: zoneBorderOp,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 18,
            }}>
              <div style={{ textAlign: "center" }}>
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" style={{ margin: "0 auto 8px" }}>
                  <path d="M12 16V8M12 8L9 11M12 8L15 11" stroke={TEAL} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M20 16.7A4 4 0 0017 9h-1.26A8 8 0 104 15.7" stroke={TEAL} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <div style={{ fontSize: 15, color: TEAL, fontWeight: 600, marginBottom: 4 }}>Drop PDF files here</div>
                <div style={{ fontSize: 12, color: MUTED }}>or click to browse</div>
              </div>
            </div>
          )}

          {FILES.map((file, i) => (
            frame >= file.start - 2 && (
              <FileCard key={i} file={file} frame={frame} fps={fps} />
            )
          ))}
        </div>

        {/* Animated divider */}
        <div style={{
          position: "absolute",
          left: VLT.x - PANEL.x - 24, top: 64,
          width: 1, height: PANEL.h - 64,
          background: `rgba(13,148,136,${divPulse * 0.25})`,
        }} />

        {/* Section label for vault */}
        <div style={{
          position: "absolute",
          left: VLT.x - PANEL.x, top: 70,
          fontSize: 13, color: MUTED, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase",
        }}>
          Knowledge Base
        </div>

        {/* Vault section */}
        <div style={{
          position: "absolute",
          left: VLT.x - PANEL.x, top: VLT.y - PANEL.y,
          width: VLT.w, height: VLT.h,
          opacity: vaultOp,
          transform: `scale(${vaultScale})`,
          transformOrigin: "center center",
        }}>
          {frame >= 230 && (
            <Vault frame={frame} fps={fps} docsIndexed={docsIndexed} />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};