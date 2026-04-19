// @ts-nocheck
/* eslint-disable */
"use client";
import React from "react";
import { Stage, Sprite, Easing, clamp, useTime, useSprite } from "./animations";

// DepScope 60s animated pitch — scenes
// Terminal-dark palette: black + green/cyan accents
// Typography: JetBrains Mono (code/data) + Geist (display/UI)

const C = {
  bg: '#050607',
  bgSoft: '#0b0d10',
  panel: '#0f1216',
  panelBorder: 'rgba(255,255,255,0.08)',
  text: '#e7ece8',
  textDim: 'rgba(231,236,232,0.55)',
  textFaint: 'rgba(231,236,232,0.28)',
  green: '#5bf2a7',      // DepScope accent
  greenSoft: 'rgba(91,242,167,0.14)',
  cyan: '#7ce4ff',
  red: '#ff6b6b',
  redSoft: 'rgba(255,107,107,0.12)',
  amber: '#ffb94a',
  grid: 'rgba(255,255,255,0.03)',
};

const FONT_MONO = 'JetBrains Mono, ui-monospace, SFMono-Regular, monospace';
const FONT_DISPLAY = 'Geist, Inter, system-ui, sans-serif';

// ─── Shared building blocks ────────────────────────────────────────────────

function GridBg({ opacity = 1 }) {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      backgroundImage: `
        linear-gradient(to right, ${C.grid} 1px, transparent 1px),
        linear-gradient(to bottom, ${C.grid} 1px, transparent 1px)
      `,
      backgroundSize: '48px 48px',
      opacity,
      pointerEvents: 'none',
    }} />
  );
}

function Scanline({ y, color = C.green, progress }) {
  return (
    <div style={{
      position: 'absolute',
      left: 0, right: 0,
      top: y,
      height: 1,
      background: `linear-gradient(to right, transparent, ${color} ${progress * 100}%, transparent)`,
      opacity: 0.6,
      pointerEvents: 'none',
    }} />
  );
}

function Caption({ text, visible = true, progress = 1 }) {
  // bottom caption bar
  const op = visible ? progress : 0;
  return (
    <div style={{
      position: 'absolute',
      left: 80, right: 80, bottom: 56,
      display: 'flex', justifyContent: 'center',
      opacity: op,
      transform: `translateY(${(1 - op) * 8}px)`,
      pointerEvents: 'none',
    }}>
      <div style={{
        fontFamily: FONT_MONO,
        fontSize: 18,
        letterSpacing: '0.02em',
        color: C.textDim,
        textAlign: 'center',
        maxWidth: 900,
      }}>
        {text}
      </div>
    </div>
  );
}

// Typewriter: reveal text char-by-char based on progress 0..1
function Typewriter({ text, progress, style }) {
  const n = Math.floor(text.length * clamp(progress, 0, 1));
  const shown = text.slice(0, n);
  const showCaret = progress < 1;
  return (
    <span style={style}>
      {shown}
      {showCaret && (
        <span style={{
          display: 'inline-block',
          width: '0.55em', height: '1em',
          background: C.green,
          marginLeft: 2,
          verticalAlign: '-0.12em',
          animation: 'caretBlink 0.9s steps(2) infinite',
        }} />
      )}
    </span>
  );
}

// ─── SCENE 1 — Problem: AI agent guesses (0 → 10s) ─────────────────────────

function SceneProblem() {
  const { localTime, progress } = useSprite();
  const t = localTime;

  // Chat bubble appears, types, then "package not found" flash
  const bubbleIn = clamp(t / 0.6, 0, 1);
  const typeProg = clamp((t - 0.8) / 2.2, 0, 1);
  const suggestLine = "npm install left-pad@1.3.0  // from training data, Jan 2023";
  const warnIn = clamp((t - 3.6) / 0.5, 0, 1);
  const badgesIn = clamp((t - 4.6) / 0.8, 0, 1);

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Top chip */}
      <div style={{
        position: 'absolute', top: 64, left: 80,
        display: 'flex', alignItems: 'center', gap: 10,
        opacity: clamp(t / 0.4, 0, 1),
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: 4,
          background: C.red,
          boxShadow: `0 0 12px ${C.red}`,
        }} />
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: C.red,
        }}>Problem · 2026</div>
      </div>

      {/* Big headline */}
      <div style={{
        position: 'absolute', top: 120, left: 80, right: 80,
        opacity: clamp((t - 0.2) / 0.5, 0, 1),
        transform: `translateY(${(1 - clamp((t - 0.2) / 0.5, 0, 1)) * 12}px)`,
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY,
          fontSize: 88,
          fontWeight: 600,
          letterSpacing: '-0.035em',
          color: C.text,
          lineHeight: 1.02,
        }}>
          Your AI agent <span style={{ color: C.red, fontStyle: 'italic' }}>guesses.</span>
        </div>
      </div>

      {/* Chat bubble mock */}
      <div style={{
        position: 'absolute',
        top: 340, left: 120,
        width: 900,
        opacity: bubbleIn,
        transform: `translateY(${(1 - bubbleIn) * 20}px)`,
      }}>
        <div style={{
          fontFamily: FONT_MONO, fontSize: 13,
          color: C.textFaint,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: 10,
        }}>agent · suggests package</div>
        <div style={{
          background: C.panel,
          border: `1px solid ${C.panelBorder}`,
          borderRadius: 14,
          padding: '22px 28px',
          fontFamily: FONT_MONO,
          fontSize: 26,
          color: C.text,
          position: 'relative',
          overflow: 'hidden',
        }}>
          <Typewriter
            text={suggestLine}
            progress={typeProg}
            style={{ color: C.text }}
          />
          {/* warning stripe overlay */}
          {warnIn > 0 && (
            <div style={{
              position: 'absolute', inset: 0,
              background: `linear-gradient(90deg, transparent 0%, ${C.redSoft} ${warnIn * 100}%, transparent 100%)`,
              pointerEvents: 'none',
            }} />
          )}
        </div>
      </div>

      {/* Red warning badges — three problems */}
      <div style={{
        position: 'absolute',
        top: 530, left: 120,
        display: 'flex', gap: 14,
        opacity: badgesIn,
        transform: `translateY(${(1 - badgesIn) * 12}px)`,
      }}>
        {[
          { label: 'Stale training data', delay: 0 },
          { label: 'Deprecated package', delay: 0.15 },
          { label: 'Known CVE', delay: 0.3 },
        ].map((b, i) => {
          const bp = clamp((t - 4.6 - b.delay) / 0.45, 0, 1);
          return (
            <div key={i} style={{
              opacity: bp,
              transform: `translateY(${(1 - bp) * 10}px) scale(${0.92 + bp * 0.08})`,
              padding: '12px 18px',
              background: C.redSoft,
              border: `1px solid ${C.red}`,
              borderRadius: 10,
              fontFamily: FONT_MONO,
              fontSize: 15,
              color: C.red,
              letterSpacing: '0.02em',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{ fontSize: 18, lineHeight: 1 }}>⚠</span>
              {b.label}
            </div>
          );
        })}
      </div>

      {/* Bottom context numbers */}
      <div style={{
        position: 'absolute',
        bottom: 100, left: 120, right: 120,
        display: 'flex', justifyContent: 'space-between',
        opacity: clamp((t - 6.5) / 0.6, 0, 1),
      }}>
        {[
          { n: 'millions', l: 'of duplicate registry fetches / day' },
          { n: '~3,000', l: 'tokens per raw JSON parse' },
          { n: '402+', l: 'CVEs slip through unchecked' },
        ].map((s, i) => (
          <div key={i}>
            <div style={{
              fontFamily: FONT_DISPLAY, fontSize: 48, fontWeight: 500,
              color: C.text, letterSpacing: '-0.03em', lineHeight: 1,
            }}>{s.n}</div>
            <div style={{
              fontFamily: FONT_MONO, fontSize: 13,
              color: C.textDim, marginTop: 6, letterSpacing: '0.02em',
            }}>{s.l}</div>
          </div>
        ))}
      </div>

      <Caption
        text="Stale training data · deprecated libs · vulnerabilities slip in"
        progress={clamp((t - 7.5) / 0.5, 0, 1)}
      />
    </div>
  );
}

// ─── SCENE 2 — Solution: one API call (10 → 22s) ───────────────────────────

function SceneSolution() {
  const { localTime } = useSprite();
  const t = localTime;

  const headlineIn = clamp(t / 0.5, 0, 1);

  // Terminal typing
  const cmdStart = 0.8;
  const cmdLine = 'curl depscope.dev/api/check/npm/express';
  const cmdProg = clamp((t - cmdStart) / 1.6, 0, 1);

  // Response typing — line-by-line reveal
  const respStart = 3.0;
  const responseLines = [
    '{',
    '  "health": {',
    '    "score": 80,',
    '    "risk": "low"',
    '  },',
    '  "recommendation": {',
    '    "action": "safe_to_use"',
    '  },',
    '  "vulnerabilities": {',
    '    "count": 0',
    '  }',
    '}',
  ];
  const respProg = clamp((t - respStart) / 3.6, 0, 1);
  const linesShown = Math.floor(responseLines.length * respProg);

  // Green pulse on "safe_to_use"
  const pulseT = t - respStart - 2.6;

  // Right side: badges snap in
  const badgeIn = clamp((t - 7.0) / 0.6, 0, 1);

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Section chip */}
      <div style={{
        position: 'absolute', top: 64, left: 80,
        display: 'flex', alignItems: 'center', gap: 10,
        opacity: clamp(t / 0.35, 0, 1),
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: 4,
          background: C.green,
          boxShadow: `0 0 12px ${C.green}`,
        }} />
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          color: C.green,
        }}>Solution · one API call</div>
      </div>

      {/* Headline */}
      <div style={{
        position: 'absolute', top: 118, left: 80, right: 80,
        opacity: headlineIn,
        transform: `translateY(${(1 - headlineIn) * 12}px)`,
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY,
          fontSize: 80, fontWeight: 600,
          letterSpacing: '-0.035em',
          color: C.text, lineHeight: 1.02,
        }}>
          DepScope <span style={{ color: C.green, fontStyle: 'italic' }}>checks.</span>
        </div>
      </div>

      {/* Terminal panel */}
      <div style={{
        position: 'absolute',
        top: 280, left: 80,
        width: 1000, height: 620,
        background: '#07090b',
        border: `1px solid ${C.panelBorder}`,
        borderRadius: 14,
        overflow: 'hidden',
        boxShadow: `0 30px 80px rgba(0,0,0,0.5), 0 0 0 1px ${C.panelBorder}`,
        opacity: clamp((t - 0.4) / 0.5, 0, 1),
      }}>
        {/* titlebar */}
        <div style={{
          height: 36, display: 'flex', alignItems: 'center',
          padding: '0 14px', gap: 8,
          background: '#0b0e11',
          borderBottom: `1px solid ${C.panelBorder}`,
        }}>
          {['#ff5f57', '#febc2e', '#28c840'].map(c => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c, opacity: 0.85 }}/>
          ))}
          <div style={{
            flex: 1, textAlign: 'center',
            fontFamily: FONT_MONO, fontSize: 12, color: C.textFaint,
          }}>~ — zsh — depscope</div>
        </div>

        {/* terminal body */}
        <div style={{
          padding: '26px 28px',
          fontFamily: FONT_MONO,
          fontSize: 18,
          lineHeight: 1.55,
          color: C.text,
        }}>
          {/* prompt line */}
          <div>
            <span style={{ color: C.green }}>➜ </span>
            <span style={{ color: C.cyan }}>~ </span>
            <Typewriter
              text={cmdLine}
              progress={cmdProg}
              style={{ color: C.text }}
            />
          </div>

          {/* response */}
          {respProg > 0 && (
            <div style={{ marginTop: 18 }}>
              {responseLines.slice(0, linesShown + 1).map((line, i) => {
                const isAction = line.includes('safe_to_use');
                const isScore = line.includes('"score"');
                const isLow = line.includes('"low"');
                const isCount = line.includes('"count": 0');

                let colored = line;
                const parts = [];
                if (isAction && pulseT > -0.3) {
                  const pulse = Math.max(0, 1 - Math.abs(pulseT) * 1.6);
                  parts.push(
                    <span key="a" style={{
                      color: C.green,
                      background: `rgba(91,242,167,${0.12 + pulse * 0.18})`,
                      padding: '2px 6px', borderRadius: 4,
                      transition: 'none',
                    }}>
                      {line}
                    </span>
                  );
                } else {
                  // simple highlight for keys/values
                  const m = line.match(/^(\s*)(".*?")(\s*:\s*)(.*)$/);
                  if (m) {
                    parts.push(
                      <span key="l" style={{ color: C.textDim }}>{m[1]}</span>,
                      <span key="k" style={{ color: C.cyan }}>{m[2]}</span>,
                      <span key="c" style={{ color: C.textDim }}>{m[3]}</span>,
                      <span key="v" style={{
                        color: /^"/.test(m[4]) ? C.green
                             : /^\d/.test(m[4]) ? C.amber
                             : C.text,
                      }}>{m[4]}</span>
                    );
                  } else {
                    parts.push(<span key="p" style={{ color: C.textDim }}>{line}</span>);
                  }
                }
                return <div key={i}>{parts}</div>;
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right side — result badges */}
      <div style={{
        position: 'absolute',
        top: 340, left: 1120, width: 720,
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        {[
          {
            k: 'Health score',
            v: '80',
            sub: 'risk: low',
            color: C.green,
            delay: 0,
          },
          {
            k: 'Recommendation',
            v: 'safe_to_use',
            sub: 'live check · 42ms',
            color: C.green,
            delay: 0.15,
          },
          {
            k: 'Vulnerabilities',
            v: '0',
            sub: 'OSV + registry advisories',
            color: C.green,
            delay: 0.3,
          },
        ].map((b, i) => {
          const bp = clamp((t - 7.0 - b.delay) / 0.5, 0, 1);
          return (
            <div key={i} style={{
              opacity: bp,
              transform: `translateX(${(1 - bp) * 24}px)`,
              background: C.panel,
              border: `1px solid ${b.color}`,
              borderLeft: `4px solid ${b.color}`,
              borderRadius: 10,
              padding: '20px 24px',
            }}>
              <div style={{
                fontFamily: FONT_MONO, fontSize: 13,
                color: C.textDim,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}>{b.k}</div>
              <div style={{
                fontFamily: FONT_DISPLAY, fontSize: 44, fontWeight: 500,
                color: b.color, letterSpacing: '-0.02em',
                marginTop: 4,
              }}>{b.v}</div>
              <div style={{
                fontFamily: FONT_MONO, fontSize: 14,
                color: C.textDim, marginTop: 2,
              }}>{b.sub}</div>
            </div>
          );
        })}
      </div>

      <Caption
        text="One endpoint · 17 ecosystems · cached · free · no auth"
        progress={clamp((t - 9.5) / 0.5, 0, 1)}
      />
    </div>
  );
}

// ─── SCENE 3 — Config: one line in CLAUDE.md (22 → 30s) ────────────────────

function SceneConfig() {
  const { localTime } = useSprite();
  const t = localTime;

  const headlineIn = clamp(t / 0.5, 0, 1);
  const fileIn = clamp((t - 0.7) / 0.5, 0, 1);
  const line = '## DEPSCOPE — Before any install: curl depscope.dev/api/check/{eco}/{pkg}';
  const lineProg = clamp((t - 1.4) / 2.2, 0, 1);
  const chipsIn = clamp((t - 4.2) / 0.6, 0, 1);

  const clients = ['Claude Code', 'Cursor', 'Windsurf', 'Copilot', 'ChatGPT', 'Any Agent'];

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Chip */}
      <div style={{
        position: 'absolute', top: 64, left: 80,
        display: 'flex', alignItems: 'center', gap: 10,
        opacity: clamp(t / 0.35, 0, 1),
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: 4,
          background: C.cyan, boxShadow: `0 0 12px ${C.cyan}`,
        }} />
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          color: C.cyan,
        }}>Integration · one line</div>
      </div>

      {/* Headline */}
      <div style={{
        position: 'absolute', top: 118, left: 80, right: 80,
        opacity: headlineIn,
        transform: `translateY(${(1 - headlineIn) * 12}px)`,
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 80, fontWeight: 600,
          letterSpacing: '-0.035em',
          color: C.text, lineHeight: 1.02,
        }}>
          Add it in <span style={{ color: C.cyan }}>one line.</span>
        </div>
        <div style={{
          fontFamily: FONT_MONO, fontSize: 20,
          color: C.textDim, marginTop: 14, letterSpacing: '0.01em',
        }}>
          Drop into your agent's config. That's it.
        </div>
      </div>

      {/* File mock */}
      <div style={{
        position: 'absolute',
        top: 340, left: 80, right: 80,
        opacity: fileIn,
        transform: `translateY(${(1 - fileIn) * 18}px)`,
      }}>
        <div style={{
          background: C.panel,
          border: `1px solid ${C.panelBorder}`,
          borderRadius: 14,
          overflow: 'hidden',
          boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
        }}>
          {/* filebar */}
          <div style={{
            display: 'flex', alignItems: 'center',
            padding: '14px 20px', gap: 12,
            background: '#0b0e11',
            borderBottom: `1px solid ${C.panelBorder}`,
            fontFamily: FONT_MONO, fontSize: 14,
            color: C.textDim,
          }}>
            <div style={{
              padding: '4px 10px',
              background: C.bg,
              border: `1px solid ${C.panelBorder}`,
              borderRadius: 6,
              color: C.text,
            }}>CLAUDE.md</div>
            <div>~/project/</div>
            <div style={{ flex: 1 }} />
            <div style={{ color: C.green }}>● saved</div>
          </div>

          {/* body */}
          <div style={{
            padding: '28px 32px',
            fontFamily: FONT_MONO, fontSize: 22,
            lineHeight: 1.7,
            minHeight: 220,
          }}>
            <div style={{ color: C.textFaint }}>
              <span style={{ color: C.textFaint, marginRight: 16 }}>1</span>
              # Project instructions
            </div>
            <div style={{ color: C.textFaint }}>
              <span style={{ color: C.textFaint, marginRight: 16 }}>2</span>
              &nbsp;
            </div>
            <div style={{ position: 'relative' }}>
              <span style={{ color: C.textFaint, marginRight: 16 }}>3</span>
              <Typewriter
                text={line}
                progress={lineProg}
                style={{ color: C.green }}
              />
              {/* highlight line */}
              {lineProg > 0 && (
                <div style={{
                  position: 'absolute',
                  left: -16, right: -16, top: -4, bottom: -4,
                  background: C.greenSoft,
                  borderLeft: `3px solid ${C.green}`,
                  borderRadius: 4,
                  zIndex: -1,
                }} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Works-with chips */}
      <div style={{
        position: 'absolute',
        bottom: 120, left: 80, right: 80,
        opacity: chipsIn,
      }}>
        <div style={{
          fontFamily: FONT_MONO, fontSize: 13,
          color: C.textDim,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          marginBottom: 14,
        }}>Works with</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {clients.map((name, i) => {
            const cp = clamp((t - 4.2 - i * 0.08) / 0.4, 0, 1);
            return (
              <div key={name} style={{
                opacity: cp,
                transform: `translateY(${(1 - cp) * 10}px) scale(${0.92 + cp * 0.08})`,
                padding: '12px 20px',
                background: C.panel,
                border: `1px solid ${C.panelBorder}`,
                borderRadius: 999,
                fontFamily: FONT_DISPLAY, fontSize: 18,
                fontWeight: 500,
                color: C.text,
              }}>{name}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── SCENE 4 — With vs Without DepScope (30 → 40s) ─────────────────────────

function SceneCompare() {
  const { localTime } = useSprite();
  const t = localTime;

  const headIn = clamp(t / 0.5, 0, 1);

  const rows = [
    { m: 'Package suggestion',  bad: 'Stale training data',      good: 'Live health check' },
    { m: 'Vulnerability check', bad: 'None',                     good: 'OSV + severity + fix' },
    { m: 'Deprecation',         bad: 'Invisible',                good: 'Flagged with reason' },
    { m: 'Discovery of issues', bad: 'In production',            good: 'Before a single line' },
  ];

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Chip */}
      <div style={{
        position: 'absolute', top: 64, left: 80,
        display: 'flex', alignItems: 'center', gap: 10,
        opacity: clamp(t / 0.35, 0, 1),
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: 4,
          background: C.green, boxShadow: `0 0 12px ${C.green}`,
        }} />
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          color: C.green,
        }}>Result · side-by-side</div>
      </div>

      {/* Headline */}
      <div style={{
        position: 'absolute', top: 118, left: 80, right: 80,
        opacity: headIn,
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 80, fontWeight: 600,
          letterSpacing: '-0.035em', color: C.text, lineHeight: 1,
        }}>
          Ship <span style={{ color: C.green, fontStyle: 'italic' }}>safer</span> code.
        </div>
      </div>

      {/* Comparison table */}
      <div style={{
        position: 'absolute',
        top: 290, left: 80, right: 80,
        display: 'grid',
        gridTemplateColumns: '1.2fr 1.4fr 1.4fr',
        gap: 0,
        border: `1px solid ${C.panelBorder}`,
        borderRadius: 16,
        overflow: 'hidden',
        background: C.panel,
      }}>
        {/* Header row */}
        {[
          { label: 'Moment', color: C.textDim },
          { label: 'Without DepScope', color: C.red },
          { label: 'With DepScope', color: C.green },
        ].map((h, i) => (
          <div key={i} style={{
            padding: '22px 28px',
            background: '#0b0e11',
            borderBottom: `1px solid ${C.panelBorder}`,
            borderRight: i < 2 ? `1px solid ${C.panelBorder}` : 'none',
            fontFamily: FONT_MONO, fontSize: 14,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: h.color,
            opacity: clamp((t - 0.4) / 0.4, 0, 1),
          }}>{h.label}</div>
        ))}

        {/* Body rows */}
        {rows.map((r, ri) => {
          const rowT = clamp((t - 1.0 - ri * 0.5) / 0.55, 0, 1);
          const isLast = ri === rows.length - 1;
          // reveal left→right within each row
          const goodT = clamp((t - 1.0 - ri * 0.5 - 0.35) / 0.5, 0, 1);
          return (
            <React.Fragment key={ri}>
              <Cell isLast={isLast} op={rowT}>
                <div style={{
                  fontFamily: FONT_DISPLAY, fontSize: 26,
                  fontWeight: 500, color: C.text, letterSpacing: '-0.01em',
                }}>{r.m}</div>
              </Cell>
              <Cell isLast={isLast} op={rowT}>
                <div style={{
                  fontFamily: FONT_MONO, fontSize: 22,
                  color: C.red,
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                  <span style={{ fontSize: 18 }}>✕</span> {r.bad}
                </div>
              </Cell>
              <Cell isLast={isLast} op={goodT} right>
                <div style={{
                  fontFamily: FONT_MONO, fontSize: 22,
                  color: C.green,
                  display: 'flex', alignItems: 'center', gap: 10,
                  opacity: goodT,
                  transform: `translateX(${(1 - goodT) * -16}px)`,
                }}>
                  <span style={{ fontSize: 18 }}>✓</span> {r.good}
                </div>
              </Cell>
            </React.Fragment>
          );
        })}
      </div>

      <Caption
        text="Issues caught before a single line is written."
        progress={clamp((t - 7.5) / 0.5, 0, 1)}
      />
    </div>
  );
}

function Cell({ children, isLast, op = 1, right }) {
  return (
    <div style={{
      padding: '24px 28px',
      borderBottom: isLast ? 'none' : `1px solid ${C.panelBorder}`,
      borderRight: right ? 'none' : `1px solid ${C.panelBorder}`,
      opacity: op,
      transform: `translateY(${(1 - op) * 8}px)`,
      display: 'flex', alignItems: 'center',
      minHeight: 72,
    }}>{children}</div>
  );
}

// ─── SCENE 5 — Energy / tokens / CO2 (40 → 50s) ────────────────────────────

function SceneEnergy() {
  const { localTime } = useSprite();
  const t = localTime;

  const headIn = clamp(t / 0.5, 0, 1);

  // big number counters
  const tokProg = clamp((t - 1.0) / 1.5, 0, 1);
  const respProg = clamp((t - 1.6) / 1.5, 0, 1);
  const pkgProg = clamp((t - 2.2) / 1.8, 0, 1);

  // fetch-fan diagram (1 fetch → N agents)
  const diagT = clamp((t - 4.0) / 2.5, 0, 1);
  const nAgents = 7;

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Chip */}
      <div style={{
        position: 'absolute', top: 64, left: 80,
        display: 'flex', alignItems: 'center', gap: 10,
        opacity: clamp(t / 0.35, 0, 1),
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: 4,
          background: C.green, boxShadow: `0 0 12px ${C.green}`,
        }} />
        <div style={{
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          color: C.green,
        }}>Efficiency by design</div>
      </div>

      {/* Headline */}
      <div style={{
        position: 'absolute', top: 118, left: 80, right: 80,
        opacity: headIn,
      }}>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 80, fontWeight: 600,
          letterSpacing: '-0.035em', color: C.text, lineHeight: 1,
        }}>
          Save tokens. <span style={{ color: C.green, fontStyle: 'italic' }}>Save energy.</span>
        </div>
      </div>

      {/* Three big counters */}
      <div style={{
        position: 'absolute',
        top: 290, left: 80, right: 80,
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24,
      }}>
        <Stat
          label="Tokens per check"
          from="3,000"
          to="<100"
          prog={tokProg}
          sub="~92% reduction"
          sym="🔤"
        />
        <Stat
          label="Response time"
          from="—"
          to="<100ms"
          prog={respProg}
          sub="cached · one fetch, many agents"
          sym="⚡"
        />
        <Stat
          label="Coverage"
          from="—"
          to="14,744+"
          prog={pkgProg}
          sub="packages · 17 ecosystems · 402 CVEs"
          sym="🔒"
        />
      </div>

      {/* Fan-out diagram */}
      <div style={{
        position: 'absolute',
        bottom: 90, left: 80, right: 80, height: 320,
        opacity: clamp((t - 3.8) / 0.5, 0, 1),
      }}>
        <div style={{
          fontFamily: FONT_MONO, fontSize: 13,
          color: C.textDim,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          marginBottom: 16,
        }}>Shared cache · 1 fetch serves every agent</div>

        <svg width="100%" height="260" viewBox="0 0 1760 260" preserveAspectRatio="xMidYMid meet">
          {/* registry node */}
          <g>
            <rect x="40" y="100" width="240" height="64" rx="10"
              fill={C.panel} stroke={C.panelBorder} />
            <text x="160" y="132" textAnchor="middle"
              fill={C.textDim}
              fontFamily={FONT_MONO} fontSize="13"
              letterSpacing="2">REGISTRY · npm/PyPI/…</text>
            <text x="160" y="152" textAnchor="middle"
              fill={C.text}
              fontFamily={FONT_DISPLAY} fontSize="16" fontWeight="500">1 fetch</text>
          </g>

          {/* arrow to cache */}
          <Arrow x1={280} y1={132} x2={480} y2={132} progress={clamp(diagT * 2, 0, 1)} color={C.green} />

          {/* cache node */}
          <g>
            <rect x="480" y="90" width="240" height="80" rx="10"
              fill={C.greenSoft} stroke={C.green} />
            <text x="600" y="120" textAnchor="middle"
              fill={C.green}
              fontFamily={FONT_MONO} fontSize="13"
              letterSpacing="2">DEPSCOPE · CACHED</text>
            <text x="600" y="148" textAnchor="middle"
              fill={C.text}
              fontFamily={FONT_DISPLAY} fontSize="18" fontWeight="500">&lt;100ms</text>
          </g>

          {/* fan-out to N agents */}
          {Array.from({ length: nAgents }).map((_, i) => {
            const y = 20 + i * (220 / (nAgents - 1));
            const show = clamp(diagT * 2 - 0.5 - i * 0.08, 0, 1);
            const x2 = 1400;
            return (
              <g key={i} style={{ opacity: show }}>
                <Arrow x1={720} y1={130} x2={x2} y2={y + 22} progress={show} color={C.cyan} dashed />
                <rect x={x2} y={y} width="280" height="44" rx="8"
                  fill={C.panel} stroke={C.panelBorder} />
                <circle cx={x2 + 22} cy={y + 22} r="5" fill={C.green} />
                <text x={x2 + 40} y={y + 27}
                  fill={C.text}
                  fontFamily={FONT_MONO} fontSize="14">
                  agent_{String(i + 1).padStart(2, '0')} · served from cache
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <Caption
        text="Less compute · less bandwidth · less CO₂ on public registries"
        progress={clamp((t - 8.0) / 0.5, 0, 1)}
      />
    </div>
  );
}

function Stat({ label, from, to, prog, sub, sym }) {
  return (
    <div style={{
      background: C.panel,
      border: `1px solid ${C.panelBorder}`,
      borderRadius: 14,
      padding: '28px 30px',
      opacity: clamp(prog * 2, 0, 1),
      transform: `translateY(${(1 - clamp(prog * 2, 0, 1)) * 10}px)`,
    }}>
      <div style={{
        fontFamily: FONT_MONO, fontSize: 13,
        color: C.textDim, letterSpacing: '0.16em',
        textTransform: 'uppercase',
      }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 18, marginTop: 10 }}>
        {from !== '—' && (
          <div style={{
            fontFamily: FONT_DISPLAY, fontSize: 40,
            color: C.red,
            textDecoration: 'line-through',
            textDecorationThickness: 2,
            opacity: 0.5,
          }}>{from}</div>
        )}
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 72,
          fontWeight: 600,
          color: C.green,
          letterSpacing: '-0.04em',
          lineHeight: 1,
          textShadow: `0 0 30px rgba(91,242,167,${0.15 + prog * 0.15})`,
        }}>{to}</div>
      </div>
      <div style={{
        fontFamily: FONT_MONO, fontSize: 14,
        color: C.textDim, marginTop: 14,
      }}>{sub}</div>
    </div>
  );
}

function Arrow({ x1, y1, x2, y2, progress, color, dashed }) {
  const ex = x1 + (x2 - x1) * progress;
  const ey = y1 + (y2 - y1) * progress;
  return (
    <g>
      <line
        x1={x1} y1={y1} x2={ex} y2={ey}
        stroke={color} strokeWidth={2}
        strokeDasharray={dashed ? '6 6' : undefined}
      />
      {progress > 0.95 && (
        <polygon
          points={`${x2},${y2} ${x2 - 10},${y2 - 5} ${x2 - 10},${y2 + 5}`}
          fill={color}
        />
      )}
    </g>
  );
}

// ─── SCENE 6 — CTA (50 → 60s) ──────────────────────────────────────────────

function SceneCTA() {
  const { localTime } = useSprite();
  const t = localTime;

  const logoIn = clamp(t / 0.7, 0, 1);
  const headIn = clamp((t - 0.4) / 0.6, 0, 1);
  const cmdIn = clamp((t - 1.2) / 0.6, 0, 1);
  const metaIn = clamp((t - 2.0) / 0.6, 0, 1);
  const urlIn = clamp((t - 2.8) / 0.6, 0, 1);

  const ecosystems = ['npm','PyPI','Cargo','Go','Composer','Maven','NuGet','RubyGems','Pub','Hex','Swift','CocoaPods','CPAN','Hackage','CRAN','Conda','Homebrew'];

  // pulsing prompt
  const pulse = Math.sin(t * 3) * 0.5 + 0.5;

  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, overflow: 'hidden' }}>
      <GridBg />

      {/* Radial glow */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(circle at 50% 45%, rgba(91,242,167,0.08), transparent 60%)`,
        opacity: clamp(t / 1, 0, 1),
      }} />

      {/* Ecosystem marquee — drifts slowly */}
      <div style={{
        position: 'absolute', top: 100, left: 0, right: 0,
        display: 'flex',
        whiteSpace: 'nowrap',
        opacity: 0.25,
        transform: `translateX(${-((t * 30) % 800)}px)`,
        pointerEvents: 'none',
      }}>
        {[...ecosystems, ...ecosystems, ...ecosystems].map((e, i) => (
          <div key={i} style={{
            fontFamily: FONT_MONO, fontSize: 18,
            color: C.textDim, padding: '0 24px',
            letterSpacing: '0.18em', textTransform: 'uppercase',
          }}>{e} ·</div>
        ))}
      </div>

      {/* Center stack */}
      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        textAlign: 'center',
      }}>
        {/* Logo mark */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16,
          opacity: logoIn,
          transform: `scale(${0.92 + logoIn * 0.08})`,
          marginBottom: 30,
        }}>
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <circle cx="28" cy="28" r="26" stroke={C.green} strokeWidth="2" />
            <circle cx="28" cy="28" r="18" stroke={C.green} strokeWidth="1.2" opacity="0.5" />
            <circle cx="28" cy="28" r="6" fill={C.green} />
            <line x1="28" y1="2" x2="28" y2="12" stroke={C.green} strokeWidth="1.5" />
            <line x1="28" y1="44" x2="28" y2="54" stroke={C.green} strokeWidth="1.5" />
            <line x1="2" y1="28" x2="12" y2="28" stroke={C.green} strokeWidth="1.5" />
            <line x1="44" y1="28" x2="54" y2="28" stroke={C.green} strokeWidth="1.5" />
          </svg>
          <div style={{
            fontFamily: FONT_DISPLAY, fontSize: 44, fontWeight: 600,
            color: C.text, letterSpacing: '-0.03em',
          }}>DepScope</div>
        </div>

        {/* Headline */}
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 100, fontWeight: 600,
          letterSpacing: '-0.04em', color: C.text, lineHeight: 1,
          opacity: headIn,
          transform: `translateY(${(1 - headIn) * 16}px)`,
          maxWidth: 1400,
        }}>
          Start with <span style={{ color: C.green, fontStyle: 'italic' }}>one curl.</span>
        </div>

        {/* Command */}
        <div style={{
          marginTop: 40,
          padding: '22px 32px',
          background: '#07090b',
          border: `1px solid ${C.green}`,
          borderRadius: 12,
          fontFamily: FONT_MONO, fontSize: 32,
          color: C.text,
          opacity: cmdIn,
          transform: `translateY(${(1 - cmdIn) * 12}px)`,
          display: 'flex', alignItems: 'center', gap: 14,
          boxShadow: `0 0 40px rgba(91,242,167,${0.12 + pulse * 0.12})`,
        }}>
          <span style={{ color: C.green }}>$</span>
          <span style={{ color: C.cyan }}>curl</span>
          <span style={{ color: C.text }}>depscope.dev/api/check/npm/express</span>
        </div>

        {/* Meta line */}
        <div style={{
          marginTop: 28,
          display: 'flex', gap: 28,
          fontFamily: FONT_MONO, fontSize: 18,
          color: C.textDim,
          opacity: metaIn,
          transform: `translateY(${(1 - metaIn) * 10}px)`,
          letterSpacing: '0.04em',
        }}>
          {['No signup', 'No API key', '17 ecosystems', 'Free'].map((m, i) => (
            <div key={m} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ color: C.green }}>✓</span> {m}
              {i < 3 && <span style={{ color: C.textFaint, marginLeft: 20 }}>·</span>}
            </div>
          ))}
        </div>

        {/* URL */}
        <div style={{
          marginTop: 50,
          fontFamily: FONT_DISPLAY, fontSize: 36, fontWeight: 500,
          color: C.green,
          letterSpacing: '-0.01em',
          opacity: urlIn,
          transform: `translateY(${(1 - urlIn) * 10}px)`,
          borderBottom: `2px solid ${C.green}`,
          paddingBottom: 4,
        }}>
          depscope.dev
        </div>

        {/* Tagline */}
        <div style={{
          marginTop: 22,
          fontFamily: FONT_MONO, fontSize: 14,
          letterSpacing: '0.2em', textTransform: 'uppercase',
          color: C.textDim,
          opacity: clamp((t - 3.6) / 0.6, 0, 1),
        }}>
          Package intelligence for AI agents
        </div>
      </div>

      {/* Footer */}
      <div style={{
        position: 'absolute', bottom: 40, left: 80, right: 80,
        display: 'flex', justifyContent: 'space-between',
        fontFamily: FONT_MONO, fontSize: 12,
        color: C.textFaint, letterSpacing: '0.12em',
        textTransform: 'uppercase',
        opacity: clamp((t - 4.5) / 0.6, 0, 1),
      }}>
        <div>© 2026 Cuttalo srl · Italy</div>
        <div>Built for AI agents</div>
      </div>
    </div>
  );
}

// ─── Master: sequence scenes on one Stage ──────────────────────────────────
// Timing (60s total):
//   0.0 → 10.0   Problem
//  10.0 → 22.0   Solution (terminal demo)
//  22.0 → 30.0   Config (one line)
//  30.0 → 40.0   With vs Without
//  40.0 → 50.0   Efficiency (stats + fan-out)
//  50.0 → 60.0   CTA

function SceneChrome() {
  const t = useTime();
  const DUR = 60;

  // Scene indicator
  const scenes = [
    { t: 0,    label: '01 · Problem' },
    { t: 10,   label: '02 · Solution' },
    { t: 22,   label: '03 · Integration' },
    { t: 30,   label: '04 · Result' },
    { t: 40,   label: '05 · Efficiency' },
    { t: 50,   label: '06 · Call to Action' },
  ];
  const idx = scenes.findIndex((s, i) => t >= s.t && (i === scenes.length - 1 || t < scenes[i + 1].t));
  const current = scenes[Math.max(0, idx)];

  return (
    <>
      {/* Top-right chapter + progress */}
      <div style={{
        position: 'absolute',
        top: 32, right: 40,
        display: 'flex', alignItems: 'center', gap: 16,
        fontFamily: FONT_MONO, fontSize: 12,
        color: C.textFaint, letterSpacing: '0.18em',
        textTransform: 'uppercase',
        zIndex: 10,
      }}>
        <div>{current.label}</div>
        <div style={{ width: 120, height: 2, background: 'rgba(255,255,255,0.08)' }}>
          <div style={{
            width: `${(t / DUR) * 100}%`, height: '100%',
            background: C.green,
            transition: 'none',
          }}/>
        </div>
        <div>{String(Math.floor(t)).padStart(2, '0')} / {DUR}s</div>
      </div>

      {/* Top-left logo */}
      <div style={{
        position: 'absolute',
        top: 28, left: 40,
        display: 'flex', alignItems: 'center', gap: 10,
        zIndex: 10,
      }}>
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <circle cx="11" cy="11" r="10" stroke={C.green} strokeWidth="1.2" />
          <circle cx="11" cy="11" r="3" fill={C.green} />
        </svg>
        <div style={{
          fontFamily: FONT_DISPLAY, fontSize: 16, fontWeight: 500,
          color: C.text, letterSpacing: '-0.01em',
        }}>DepScope</div>
      </div>
    </>
  );
}

function App() {
  return (
    <Stage
      width={1920}
      height={1080}
      duration={60}
      background={C.bg}
      persistKey="depscope-pitch"
    >
      <SceneChrome />
      <Sprite start={0}    end={10}>  <SceneProblem  /> </Sprite>
      <Sprite start={10}   end={22}>  <SceneSolution /> </Sprite>
      <Sprite start={22}   end={30}>  <SceneConfig   /> </Sprite>
      <Sprite start={30}   end={40}>  <SceneCompare  /> </Sprite>
      <Sprite start={40}   end={50}>  <SceneEnergy   /> </Sprite>
      <Sprite start={50}   end={60}>  <SceneCTA      /> </Sprite>
    </Stage>
  );
}

export default App;
