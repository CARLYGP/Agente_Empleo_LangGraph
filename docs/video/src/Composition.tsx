import React from "react";
import { AbsoluteFill, Composition, useCurrentFrame } from "remotion";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

const { fontFamily: MONO } = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });

/**
 * Tarjeta animada del perfil: el StateGraph real de agente/grafo.py recorrido por las ofertas.
 * 15 portales (Send) → filtro → evaluadores en paralelo (Groq) → priorizar →
 * taller redactor ⇄ revisor (Groq) → resumen → interrupt humano → postular.
 * Todo es periódico con PERIODO frames para que el GIF cierre sin salto.
 */

const PERIODO = 240;
const W = 800;
const H = 600;

const COL = {
  fondo: "#070B14",
  groq: "#F55036",
  borde: "rgba(255,255,255,0.14)",
  arista: "rgba(148,163,184,0.20)",
  texto: "#C7D0E0",
  tenue: "#7C879C",
  cian: "#22D3EE",
  ambar: "#F5A524",
  verde: "#34D399",
  rosa: "#F43F5E",
};

const GROQ =
  "M12.036 2c-3.853-.035-7 3-7.036 6.781-.035 3.782 3.055 6.872 6.908 6.907h2.42v-2.566h-2.292c-2.407.028-4.38-1.866-4.408-4.23-.029-2.362 1.901-4.298 4.308-4.326h.1c2.407 0 4.358 1.915 4.365 4.278v6.305c0 2.342-1.944 4.25-4.323 4.279a4.375 4.375 0 01-3.033-1.252l-1.851 1.818A7 7 0 0012.029 22h.092c3.803-.056 6.858-3.083 6.879-6.816v-6.5C18.907 4.963 15.817 2 12.036 2z";

type P = [number, number];

// ---------- nodos ----------
const N = {
  filtro: [250, 200] as P,
  ev0: [410, 112] as P,
  ev1: [410, 200] as P,
  ev2: [410, 288] as P,
  prior: [570, 200] as P,
  redactor: [680, 330] as P,
  revisor: [680, 470] as P,
  resumen: [540, 470] as P,
  humano: [380, 470] as P,
  postular: [220, 470] as P,
};
const PORTALES: P[] = Array.from({ length: 15 }, (_, i) => {
  const a = (-62 + (124 * i) / 14) * (Math.PI / 180);
  return [175 - Math.cos(a) * 105, 200 + Math.sin(a) * 125];
});

// ---------- aristas: curvas cúbicas ----------
type Arista = { a: P; c1: P; c2: P; b: P };
const recta = (a: P, b: P, curva = 0.45): Arista => {
  const dx = (b[0] - a[0]) * curva;
  return { a, c1: [a[0] + dx, a[1]], c2: [b[0] - dx, b[1]], b };
};
const punto = (e: Arista, t: number): P => {
  const u = 1 - t;
  const f = (k: 0 | 1) => u * u * u * e.a[k] + 3 * u * u * t * e.c1[k] + 3 * u * t * t * e.c2[k] + t * t * t * e.b[k];
  return [f(0), f(1)];
};
const d = (e: Arista) => `M${e.a[0]},${e.a[1]} C${e.c1[0]},${e.c1[1]} ${e.c2[0]},${e.c2[1]} ${e.b[0]},${e.b[1]}`;

/** Recorta la arista para que arranque y termine en el borde de los nodos. */
const entre = (a: P, ra: number, b: P, rb: number, curva = 0.45, c?: [P, P]): Arista => {
  const e = c ? { a, c1: c[0], c2: c[1], b } : recta(a, b, curva);
  const ini = punto(e, 0.001);
  const fin = punto(e, 0.999);
  // dirección aproximada en cada extremo
  const da = norm([e.c1[0] - a[0], e.c1[1] - a[1]], [ini[0] - a[0], ini[1] - a[1]]);
  const db = norm([e.c2[0] - b[0], e.c2[1] - b[1]], [fin[0] - b[0], fin[1] - b[1]]);
  const a2: P = [a[0] + da[0] * ra, a[1] + da[1] * ra];
  const b2: P = [b[0] + db[0] * rb, b[1] + db[1] * rb];
  return { a: a2, c1: e.c1, c2: e.c2, b: b2 };
};
const norm = (v: P, alt: P): P => {
  const l = Math.hypot(v[0], v[1]);
  if (l < 1e-6) {
    const l2 = Math.hypot(alt[0], alt[1]) || 1;
    return [alt[0] / l2, alt[1] / l2];
  }
  return [v[0] / l, v[1] / l];
};

const R = 30; // radio de los nodos
const RG = 27; // radio de los nodos Groq

type Flujo = { e: Arista; inicio: number; dur: number; color: string; tam?: number };

const FLUJOS: Flujo[] = [];
const ARISTAS: { e: Arista; color?: string; guion?: boolean }[] = [];

// 15 portales → filtro (fan-out con Send, cada portal termina a su ritmo)
PORTALES.forEach((p, i) => {
  const e = entre(p, 6, N.filtro, R, 0.5);
  ARISTAS.push({ e });
  FLUJOS.push({ e, inicio: ((i * 7) % 15) * 1.3, dur: 30, color: COL.cian, tam: 3.2 });
});
// filtro → evaluadores (Send por oferta) → priorizar
(["ev0", "ev1", "ev2"] as const).forEach((k, i) => {
  const e1 = entre(N.filtro, R, N[k], RG);
  const e2 = entre(N[k], RG, N.prior, R);
  ARISTAS.push({ e: e1 }, { e: e2 });
  FLUJOS.push({ e: e1, inicio: 50 + i * 3, dur: 22, color: COL.cian });
  FLUJOS.push({ e: e2, inicio: 108 + i * 5, dur: 22, color: COL.groq });
});
// priorizar → taller (arista condicional: solo las que superan el umbral)
const ePR = entre(N.prior, R, N.redactor, RG, 0, [
  [640, 200],
  [680, 250],
]);
ARISTAS.push({ e: ePR });
FLUJOS.push({ e: ePR, inicio: 140, dur: 18, color: COL.groq, tam: 4.4 });

// ciclo redactor ⇄ revisor
const eRV = entre(N.redactor, RG, N.revisor, RG, 0, [
  [728, 372],
  [728, 428],
]);
const eVR = entre(N.revisor, RG, N.redactor, RG, 0, [
  [632, 428],
  [632, 372],
]);
ARISTAS.push({ e: eRV }, { e: eVR, color: "rgba(244,63,94,0.28)" });
FLUJOS.push({ e: eRV, inicio: 166, dur: 14, color: COL.groq, tam: 4.4 });
FLUJOS.push({ e: eVR, inicio: 186, dur: 12, color: COL.rosa, tam: 4.4 }); // el revisor devuelve la carta
FLUJOS.push({ e: eRV, inicio: 200, dur: 12, color: COL.groq, tam: 4.4 });

// revisor → resumen → humano → postular
const eVN = entre(N.revisor, RG, N.resumen, R);
const eNH = entre(N.resumen, R, N.humano, R);
const eHP = entre(N.humano, R, N.postular, R);
ARISTAS.push({ e: eVN }, { e: eNH }, { e: eHP, color: "rgba(245,165,36,0.35)", guion: true });
FLUJOS.push({ e: eVN, inicio: 214, dur: 14, color: COL.groq, tam: 4.4 });
FLUJOS.push({ e: eNH, inicio: 230, dur: 14, color: COL.cian, tam: 4.4 });
FLUJOS.push({ e: eHP, inicio: 22, dur: 20, color: COL.ambar, tam: 4.4 }); // tras la aprobación (vuelve a empezar el ciclo)

// ---------- tiempo periódico ----------
const fase = (frame: number, desde: number) => (((frame - desde) % PERIODO) + PERIODO) % PERIODO;
const brillo = (frame: number, llegada: number, dur = 26) => {
  const t = fase(frame, llegada);
  return t < dur ? Math.exp(-t / (dur / 3)) : 0;
};
const activo = (frame: number, desde: number, dur: number) => fase(frame, desde) < dur;

// ---------- íconos simples ----------
const Icono: React.FC<{ tipo: string; c: P; color: string }> = ({ tipo, c, color }) => {
  const [x, y] = c;
  const s = { fill: "none", stroke: color, strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (tipo) {
    case "filtro":
      return <path d={`M${x - 11},${y - 9} H${x + 11} L${x + 3},${y + 1} V${y + 9} L${x - 3},${y + 6} V${y + 1} Z`} {...s} />;
    case "prior":
      return (
        <g {...s}>
          <path d={`M${x - 10},${y + 9} V${y + 1}`} />
          <path d={`M${x},${y + 9} V${y - 9}`} />
          <path d={`M${x + 10},${y + 9} V${y - 3}`} />
        </g>
      );
    case "resumen":
      return (
        <g {...s}>
          <rect x={x - 12} y={y - 8} width={24} height={16} rx={2.5} />
          <path d={`M${x - 11},${y - 6.5} L${x},${y + 1.5} L${x + 11},${y - 6.5}`} />
        </g>
      );
    case "humano":
      return (
        <g {...s}>
          <circle cx={x} cy={y - 5} r={4.5} />
          <path d={`M${x - 9},${y + 10} C${x - 9},${y + 1} ${x + 9},${y + 1} ${x + 9},${y + 10}`} />
        </g>
      );
    case "postular":
      return (
        <g {...s}>
          <path d={`M${x - 11},${y - 1} L${x + 11},${y - 9} L${x + 4},${y + 10} L${x},${y + 2} Z`} />
          <path d={`M${x},${y + 2} L${x + 11},${y - 9}`} />
        </g>
      );
    default:
      return null;
  }
};

const Nodo: React.FC<{ c: P; tipo: string; etiqueta?: string; luz: number; color: string; pausa?: boolean }> = ({ c, tipo, etiqueta, luz, color, pausa }) => (
  <g>
    <circle cx={c[0]} cy={c[1]} r={R + 10 * luz} fill={color} opacity={0.16 * luz} />
    <circle cx={c[0]} cy={c[1]} r={R} fill="#0D1322" stroke={luz > 0.05 ? color : COL.borde} strokeOpacity={0.35 + 0.65 * luz} strokeWidth={1.6} />
    <Icono tipo={tipo} c={c} color={luz > 0.05 || pausa ? color : COL.texto} />
    {etiqueta && (
      <text x={c[0]} y={c[1] + R + 20} textAnchor="middle" fontFamily={MONO} fontSize={13} fill={COL.tenue}>
        {etiqueta}
      </text>
    )}
  </g>
);

const NodoGroq: React.FC<{ c: P; luz: number; pensando: boolean; frame: number; etiqueta?: string }> = ({ c, luz, pensando, frame, etiqueta }) => {
  const s = 1.25;
  const act = Math.max(luz, pensando ? 1 : 0); // en reposo queda apagado; se enciende cuando el LLM trabaja
  return (
    <g>
      <circle cx={c[0]} cy={c[1]} r={RG + 12 * luz} fill={COL.groq} opacity={0.22 * luz} />
      <circle cx={c[0]} cy={c[1]} r={RG} fill="#1A0F12" stroke={COL.groq} strokeOpacity={0.55 + 0.45 * act} strokeWidth={1.6} />
      <circle cx={c[0]} cy={c[1]} r={RG} fill={COL.groq} opacity={act} />
      {pensando && (
        <circle
          cx={c[0]}
          cy={c[1]}
          r={RG + 6}
          fill="none"
          stroke={COL.groq}
          strokeWidth={2}
          strokeDasharray="10 8"
          strokeLinecap="round"
          transform={`rotate(${frame * 6} ${c[0]} ${c[1]})`}
          opacity={0.9}
        />
      )}
      <path d={GROQ} fill={COL.groq} transform={`translate(${c[0] - 12 * s} ${c[1] - 12 * s}) scale(${s})`} />
      <path d={GROQ} fill="#fff" opacity={act} transform={`translate(${c[0] - 12 * s} ${c[1] - 12 * s}) scale(${s})`} />
      {etiqueta && (
        <text x={c[0]} y={c[1] + RG + 20} textAnchor="middle" fontFamily={MONO} fontSize={13} fill={COL.tenue}>
          {etiqueta}
        </text>
      )}
    </g>
  );
};

const Particula: React.FC<{ f: Flujo; frame: number }> = ({ f, frame }) => {
  const t = fase(frame, f.inicio);
  if (t > f.dur) return null;
  const p = t / f.dur;
  const tam = f.tam ?? 3.6;
  return (
    <g>
      {[0.12, 0.08, 0.04].map((k, i) => {
        const q = p - k;
        if (q < 0) return null;
        const [x, y] = punto(f.e, q);
        return <circle key={i} cx={x} cy={y} r={tam * (0.45 + i * 0.15)} fill={f.color} opacity={0.18 + i * 0.15} />;
      })}
      {(() => {
        const [x, y] = punto(f.e, p);
        return <circle cx={x} cy={y} r={tam} fill={f.color} style={{ filter: `drop-shadow(0 0 6px ${f.color})` }} />;
      })()}
    </g>
  );
};

export const TarjetaAgente: React.FC = () => {
  const frame = useCurrentFrame();
  const llegadaPortales = 22 + 30;

  return (
    <AbsoluteFill style={{ backgroundColor: COL.fondo }}>
      <AbsoluteFill style={{ background: `radial-gradient(520px 380px at 70% 62%, ${COL.groq}1A, transparent 70%)` }} />
      <AbsoluteFill style={{ background: `radial-gradient(480px 360px at 22% 30%, ${COL.cian}14, transparent 70%)` }} />
      <AbsoluteFill
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          maskImage: "radial-gradient(ellipse at center, black 35%, transparent 80%)",
        }}
      />
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {ARISTAS.map((a, i) => (
          <path key={i} d={d(a.e)} fill="none" stroke={a.color ?? COL.arista} strokeWidth={1.5} strokeDasharray={a.guion ? "5 6" : undefined} />
        ))}

        {/* portales: 15 nodos buscar_portal en paralelo */}
        {PORTALES.map((p, i) => {
          const luz = brillo(frame, PERIODO - 8 + ((i * 7) % 15) * 1.3, 18);
          return <circle key={i} cx={p[0]} cy={p[1]} r={5 + luz * 2} fill={COL.cian} opacity={0.45 + luz * 0.55} />;
        })}
        <text x={118} y={348} textAnchor="middle" fontFamily={MONO} fontSize={13} fill={COL.tenue}>
          15 portales
        </text>

        {FLUJOS.map((f, i) => (
          <Particula key={i} f={f} frame={frame} />
        ))}

        <Nodo c={N.filtro} tipo="filtro" etiqueta="filtro" luz={brillo(frame, llegadaPortales)} color={COL.cian} />
        {(["ev0", "ev1", "ev2"] as const).map((k, i) => (
          <NodoGroq key={k} c={N[k]} frame={frame} luz={brillo(frame, 72 + i * 3)} pensando={activo(frame, 72 + i * 3, 36 + i * 5)} etiqueta={i === 2 ? "evaluadores" : undefined} />
        ))}
        <Nodo c={N.prior} tipo="prior" etiqueta="priorizar" luz={brillo(frame, 132)} color={COL.groq} />
        <NodoGroq c={N.redactor} frame={frame} luz={Math.max(brillo(frame, 158), brillo(frame, 198))} pensando={activo(frame, 158, 8) || activo(frame, 198, 2)} />
        <NodoGroq c={N.revisor} frame={frame} luz={Math.max(brillo(frame, 180), brillo(frame, 212))} pensando={activo(frame, 180, 6) || activo(frame, 212, 2)} />
        <text x={718} y={318} fontFamily={MONO} fontSize={13} fill={COL.tenue}>
          redactor
        </text>
        <text x={718} y={492} fontFamily={MONO} fontSize={13} fill={COL.tenue}>
          revisor
        </text>
        <Nodo c={N.resumen} tipo="resumen" etiqueta="resumen" luz={brillo(frame, 228)} color={COL.cian} />
        <Nodo c={N.humano} tipo="humano" etiqueta="tú apruebas" luz={Math.max(brillo(frame, 244 - PERIODO, 40), 0.25 + 0.25 * Math.sin((frame / PERIODO) * Math.PI * 4))} color={COL.ambar} pausa />
        <Nodo c={N.postular} tipo="postular" etiqueta="postular" luz={brillo(frame, 42)} color={COL.verde} />
      </svg>
    </AbsoluteFill>
  );
};

export const Composiciones: React.FC = () => (
  <Composition id="TarjetaAgente" component={TarjetaAgente} durationInFrames={PERIODO} fps={30} width={W} height={H} />
);
