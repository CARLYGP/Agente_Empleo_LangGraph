import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import datos from "./datos.json";
import { Escritorio, Globo, Hoja, Lienzo, LogoGroq, Sobre, Trabajador, Tipo } from "./personajes";
import { C, Encabezado, Fondo, MONO, SANS, Tarjeta, fmt, prog } from "./tema";

type Oferta = (typeof datos.ofertas)[number];
const OF = datos.ofertas as Oferta[];
const CANDIDATAS = OF.filter((o) => o.pasa);
const miles = (n: number) => n.toLocaleString("es-CO");
const seg = (s: number) => fmt(s, 1) + " s";

/** Interpolación con clamp entre dos puntos. */
const lerp = (f: number, a: number, b: number, v0: number, v1: number) => interpolate(f, [a, b], [v0, v1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Pie: React.FC<{ children: React.ReactNode; desde?: number; color?: string }> = ({ children, desde = 30, color = C.tenue }) => {
  const frame = useCurrentFrame();
  const a = prog(frame, desde, 26);
  return (
    <div style={{ position: "absolute", left: 120, right: 120, bottom: 64, fontFamily: MONO, fontSize: 24, color, opacity: a, translate: `0 ${(1 - a) * 14}px` }}>{children}</div>
  );
};

const Chip: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ children, color = C.tenue, style }) => (
  <span style={{ display: "inline-block", padding: "6px 14px", borderRadius: 999, border: `1px solid ${color}55`, background: `${color}14`, color, fontFamily: MONO, fontSize: 20, ...style }}>{children}</span>
);

const corto = (o: Oferta) =>
  ({
    "Ingeniero de IA Junior (agentes LLM)": "IA Junior · agentes LLM",
    "Analista de Datos Junior - Power BI": "Analista Jr · Power BI",
    "Junior AI Engineer (Computer Vision)": "Jr AI Eng. · Visión",
    "Senior Data Architect": "Senior Data Architect",
    "Data Analyst (Tableau, AWS)": "Data Analyst · Tableau",
  })[o.titulo] ?? o.titulo;

// =====================================================================
// 1. Portada
// =====================================================================
const EQUIPO: { tipo: Tipo; nombre: string }[] = [
  { tipo: "bot", nombre: "buscador" },
  { tipo: "bot", nombre: "filtro" },
  { tipo: "groq", nombre: "evaluador" },
  { tipo: "groq", nombre: "redactor" },
  { tipo: "groq", nombre: "revisor" },
  { tipo: "bot", nombre: "notificador" },
  { tipo: "humano", nombre: "tú" },
  { tipo: "bot", nombre: "postulador" },
];

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const sub = prog(frame, 44, 30);
  return (
    <AbsoluteFill>
      <Fondo acento={C.groq} />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 170 }}>
        {["Un equipo de agentes", "que busca empleo por ti"].map((l, i) => {
          const a = prog(frame, 8 + i * 9, 32);
          return (
            <div key={l} style={{ overflow: "hidden", paddingBottom: 8 }}>
              <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 112, lineHeight: 1.04, letterSpacing: -4, color: C.texto, translate: `0 ${(1 - a) * 150}px`, textAlign: "center" }}>{l}</div>
            </div>
          );
        })}
        <div style={{ fontFamily: SANS, fontSize: 36, color: C.tenue, marginTop: 24, opacity: sub, translate: `0 ${(1 - sub) * 20}px` }}>
          <span style={{ color: C.cian, fontWeight: 700 }}>LangGraph</span> organiza el trabajo · <span style={{ color: C.groq, fontWeight: 700 }}>Groq</span> piensa · <span style={{ color: C.ambar, fontWeight: 700 }}>tú</span> apruebas cada envío
        </div>
      </AbsoluteFill>
      <Lienzo>
        {EQUIPO.map((e, i) => {
          const x = 330 + i * 180;
          const entra = prog(frame, 20 + i * 5, 40);
          const desde = i < 4 ? -200 : 2120;
          const xx = desde + (x - desde) * entra;
          return (
            <g key={i}>
              <Trabajador x={xx} y={960} t={frame + i * 13} tipo={e.tipo} accion={entra < 0.97 ? "caminar" : frame > 110 && i % 3 === 0 ? "saludar" : "quieto"} mira={i < 4 ? 1 : -1} escala={0.85} />
              <text x={x} y={1010} textAnchor="middle" fontFamily={MONO} fontSize={19} fill={C.tenue} opacity={prog(frame, 60 + i * 4, 20)}>
                {e.nombre}
              </text>
            </g>
          );
        })}
      </Lienzo>
    </AbsoluteFill>
  );
};

// =====================================================================
// 2. El grafo como oficina
// =====================================================================
type Puesto = { x: number; y: number; nombre: string; patron: string; color: string; gente: Tipo[] };
const PUESTOS: Puesto[] = [
  { x: 250, y: 520, nombre: "buscadores", patron: "Send ×15", color: C.cian, gente: ["bot", "bot", "bot"] },
  { x: 580, y: 520, nombre: "filtro", patron: "reglas · 0 tokens", color: C.cian, gente: ["bot"] },
  { x: 920, y: 520, nombre: "evaluadores", patron: "Send ×N · LLM", color: C.groq, gente: ["groq", "groq", "groq"] },
  { x: 1260, y: 520, nombre: "priorizar", patron: "60 / 40", color: C.cian, gente: ["bot"] },
  { x: 1620, y: 520, nombre: "redactor ⇄ revisor", patron: "ciclo ≤ 3", color: C.groq, gente: ["groq", "groq"] },
  { x: 1620, y: 860, nombre: "notificador", patron: "resumen diario", color: C.cian, gente: ["bot"] },
  { x: 1140, y: 860, nombre: "tú", patron: "interrupt()", color: C.ambar, gente: ["humano"] },
  { x: 660, y: 860, nombre: "postulador", patron: "correo + CV", color: C.verde, gente: ["bot"] },
];

export const Equipo: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Fondo acento={C.cian} />
      <Encabezado etiqueta="agente/grafo.py · StateGraph" titulo="Cada nodo es un puesto de trabajo" color={C.cian} />
      <Lienzo>
        {PUESTOS.slice(0, -1).map((p, i) => {
          const q = PUESTOS[i + 1];
          const a = prog(frame, 30 + i * 14, 30);
          const vertical = p.x === q.x;
          const x1 = vertical ? p.x : p.x + 120;
          const y1 = vertical ? p.y + 100 : p.y - 50;
          const x2 = vertical ? q.x : q.x + (q.x < p.x ? 120 : -120);
          const y2 = vertical ? q.y - 130 : q.y - 50;
          const largo = Math.hypot(x2 - x1, y2 - y1);
          const tt = ((frame - 40 - i * 14) % 60) / 60;
          return (
            <g key={i}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(148,163,184,0.35)" strokeWidth={3} strokeDasharray={largo} strokeDashoffset={largo * (1 - a)} />
              {a > 0.99 && tt >= 0 && <circle cx={x1 + (x2 - x1) * tt} cy={y1 + (y2 - y1) * tt} r={6} fill={p.color} style={{ filter: `drop-shadow(0 0 8px ${p.color})` }} />}
            </g>
          );
        })}
        {PUESTOS.map((p, i) => {
          const a = prog(frame, 14 + i * 10, 30);
          const n = p.gente.length;
          return (
            <g key={p.nombre} opacity={a} transform={`translate(0 ${(1 - a) * 40})`}>
              <ellipse cx={p.x} cy={p.y + 6} rx={130} ry={26} fill={p.color} opacity={0.08} />
              {p.gente.map((g, k) => (
                <Trabajador key={k} x={p.x + (k - (n - 1) / 2) * 62} y={p.y} t={frame + i * 9 + k * 17} tipo={g} accion={g === "humano" ? "quieto" : k % 2 ? "teclear" : "leer"} escala={0.5} />
              ))}
              <text x={p.x} y={p.y + 50} textAnchor="middle" fontFamily={SANS} fontWeight={700} fontSize={26} fill={C.texto}>
                {p.nombre}
              </text>
              <text x={p.x} y={p.y + 80} textAnchor="middle" fontFamily={MONO} fontSize={19} fill={p.color}>
                {p.patron}
              </text>
            </g>
          );
        })}
      </Lienzo>
      <Pie desde={140}>Todos leen y escriben el mismo estado; LangGraph decide quién trabaja, cuándo y en paralelo.</Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 3. Buscadores: 15 portales a la vez
// =====================================================================
const PORTALES = ["Computrabajo", "elempleo", "LinkedIn", "Get on Board", "Remotive", "RemoteOK", "Himalayas", "Jobicy", "Working Nomads", "We Work Remotely", "Remote Rocketship", "Arc.dev", "hiring.lat", "Remote Latinos", "Workana"];

export const Buscadores: React.FC = () => {
  const frame = useCurrentFrame();
  const base: [number, number] = [430, 860];
  const cuenta = Math.round(lerp(frame, 120, 200, 0, 1354));
  return (
    <AbsoluteFill>
      <Fondo acento={C.cian} />
      <Encabezado etiqueta="1 · agente buscador" titulo="15 portales al mismo tiempo" color={C.cian} />
      <Lienzo>
        {PORTALES.map((nombre, i) => {
          const c = i % 5;
          const r = Math.floor(i / 5);
          const x = 900 + c * 205;
          const y = 330 + r * 170;
          const a = prog(frame, 6 + i * 2, 24);
          const lleno = frame > 80 + (i % 7) * 3;
          return (
            <g key={nombre} opacity={a}>
              <rect x={x - 92} y={y - 44} width={184} height={88} rx={14} fill="rgba(255,255,255,0.035)" stroke={lleno ? `${C.cian}88` : "rgba(255,255,255,0.12)"} />
              <text x={x} y={y + 7} textAnchor="middle" fontFamily={MONO} fontSize={nombre.length > 13 ? 15 : 18} fill={C.texto}>
                {nombre}
              </text>
            </g>
          );
        })}
        {/* sede: donde se juntan las ofertas */}
        <rect x={base[0] - 150} y={base[1] - 16} width={300} height={22} rx={8} fill="#24324D" />
        {Array.from({ length: Math.min(15, Math.max(0, Math.floor((frame - 150) / 3))) }).map((_, k) => (
          <Hoja key={k} x={base[0] - 90 + (k % 5) * 45} y={base[1] - 40 - Math.floor(k / 5) * 14} ancho={60} rot={(k * 37) % 9 - 4} />
        ))}
        {PORTALES.map((_, i) => {
          const c = i % 5;
          const r = Math.floor(i / 5);
          const destino: [number, number] = [900 + c * 205, 330 + r * 170 + 80];
          const ida = prog(frame, 24 + i * 2, 50);
          const vuelta = prog(frame, 92 + (i % 7) * 3, 56);
          const t = vuelta > 0 ? vuelta : ida;
          const desde = vuelta > 0 ? destino : base;
          const hasta = vuelta > 0 ? base : destino;
          const x = desde[0] + (hasta[0] - desde[0]) * t + (vuelta > 0 ? 0 : 0);
          const y = desde[1] + (hasta[1] - desde[1]) * t;
          if (vuelta >= 1) return null;
          const moviendo = (ida > 0 && ida < 1) || vuelta > 0;
          return (
            <Trabajador
              key={i}
              x={x + ((i % 3) - 1) * (1 - t) * 30 * (vuelta > 0 ? 0 : 1)}
              y={y}
              t={frame + i * 11}
              tipo="bot"
              escala={0.36}
              accion={vuelta > 0 ? "cargar" : moviendo ? "caminar" : "leer"}
              mira={vuelta > 0 ? -1 : 1}
              objeto={vuelta > 0 ? <Hoja x={62} y={-95} ancho={60} /> : undefined}
            />
          );
        })}
      </Lienzo>
      <div style={{ position: "absolute", left: 120, top: 300, width: 600 }}>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.tenue, opacity: prog(frame, 110, 20) }}>corrida diaria real · 11/11/2026</div>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 92, color: C.texto, letterSpacing: -3, opacity: prog(frame, 116, 20) }}>{miles(cuenta)}</div>
        <div style={{ fontFamily: SANS, fontSize: 30, color: C.tenue, opacity: prog(frame, 116, 20) }}>ofertas revisadas en</div>
        <div style={{ display: "flex", gap: 18, alignItems: "baseline", marginTop: 10, opacity: prog(frame, 140, 24) }}>
          <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 56, color: C.cian }}>1 min 16 s</span>
          <span style={{ fontFamily: MONO, fontSize: 24, color: C.tenue, textDecoration: "line-through" }}>4 min 38 s</span>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 20, color: C.tenue, marginTop: 6, opacity: prog(frame, 150, 24) }}>la versión 1 iba portal por portal</div>
      </div>
      <Pie desde={190} color={C.cian}>En la demo que sigue: 5 ofertas de ejemplo y el modelo real (openai/gpt-oss-120b en Groq).</Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 4. Filtro: el inspector sella las ofertas
// =====================================================================
const MOTIVO: Record<string, string> = {
  "Senior Data Architect": "título fuera del perfil",
  "Data Analyst (Tableau, AWS)": "pide 5 años de experiencia",
};

export const Filtro: React.FC = () => {
  const frame = useCurrentFrame();
  const INSPECTOR = 960;
  const CINTA = 720;
  const PASO = 34;
  return (
    <AbsoluteFill>
      <Fondo acento={C.cian} />
      <Encabezado etiqueta="2 · filtro" titulo="Reglas primero, tokens después" color={C.cian} />
      <Lienzo>
        {/* cinta transportadora */}
        <rect x={120} y={CINTA + 50} width={1680} height={18} rx={9} fill="#1E293B" />
        {Array.from({ length: 42 }).map((_, k) => (
          <rect key={k} x={120 + ((k * 40 + frame * 3) % 1680)} y={CINTA + 55} width={18} height={8} rx={4} fill="#334155" />
        ))}
        {OF.map((o, k) => {
          const llega = 20 + k * PASO;
          const x0 = lerp(frame, llega - 30, llega, 160, INSPECTOR);
          const sello = prog(frame, llega + 8, 8);
          const sale = prog(frame, llega + 18, 22);
          const pasa = o.pasa;
          const x = pasa ? x0 + sale * (1500 - INSPECTOR + (CANDIDATAS.indexOf(o) - 1) * 225) : x0;
          const y = pasa ? CINTA - sale * 40 * 0 : CINTA + sale * 180;
          if (frame < llega - 30) return null;
          return (
            <g key={o.url}>
              <Hoja
                x={x}
                y={y}
                ancho={200}
                titulo={corto(o)}
                color={pasa ? C.verde : C.rosa}
                opacidad={pasa ? 1 : 1 - sale * 0.85}
                rot={pasa ? 0 : sale * 18}
                sello={{ texto: pasa ? "PASA" : "DESCARTADA", color: pasa ? C.verde : C.rosa, a: sello }}
              />
              {!pasa && sello > 0 && (
                <text x={INSPECTOR} y={CINTA + 140 + sale * 40} textAnchor="middle" fontFamily={MONO} fontSize={22} fill={C.rosa} opacity={sello * (1 - sale)}>
                  {MOTIVO[o.titulo]}
                </text>
              )}
            </g>
          );
        })}
        <Trabajador x={INSPECTOR - 150} y={CINTA + 40} t={frame} tipo="bot" accion={frame > 20 && frame < 20 + OF.length * PASO ? "sellar" : "quieto"} escala={0.95} />
        <text x={1500} y={CINTA - 100} textAnchor="middle" fontFamily={MONO} fontSize={22} fill={C.verde} opacity={prog(frame, 60, 20)}>
          candidatas
        </text>
      </Lienzo>
      <Pie desde={200}>
        {datos.revisadas} revisadas · {CANDIDATAS.length} pasan · 0 tokens: lo que se puede decidir con reglas no se le pregunta al LLM.
      </Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 5. Evaluadores en paralelo
// =====================================================================
const Medidor: React.FC<{ x: number; y: number; valor: number; a: number }> = ({ x, y, valor, a }) => {
  const r = 70;
  const v = valor * a;
  const ang = Math.PI * (1 - v / 100);
  const fin = [x + Math.cos(ang) * r, y - Math.sin(ang) * r];
  return (
    <g>
      <path d={`M${x - r},${y} A${r},${r} 0 0 1 ${x + r},${y}`} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={14} strokeLinecap="round" />
      {a > 0 && <path d={`M${x - r},${y} A${r},${r} 0 0 1 ${fin[0]},${fin[1]}`} fill="none" stroke={C.groq} strokeWidth={14} strokeLinecap="round" />}
      <text x={x} y={y - 6} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={48} fill={C.texto}>
        {Math.round(v)}
      </text>
      <text x={x} y={y + 24} textAnchor="middle" fontFamily={MONO} fontSize={16} fill={C.tenue}>
        / 100
      </text>
    </g>
  );
};

export const Evaluadores: React.FC = () => {
  const frame = useCurrentFrame();
  const fin = [110, 150, 190]; // cuándo termina cada escritorio (el orden real de las respuestas no se asigna a una oferta)
  return (
    <AbsoluteFill>
      <Fondo acento={C.groq} />
      <Encabezado etiqueta="3 · agente evaluador · LLM" titulo="Tres agentes Groq leen en paralelo" color={C.groq} />
      <Lienzo>
        {CANDIDATAS.map((o, i) => {
          const x = 380 + i * 580;
          const listo = prog(frame, fin[i], 24);
          const pensando = frame > 30 && listo < 1;
          return (
            <g key={o.url}>
              <Hoja x={x - 70} y={350} ancho={150} titulo={corto(o).slice(0, 15)} color={C.cian} opacidad={prog(frame, 10 + i * 6, 20)} rot={-4} />
              <g opacity={prog(frame, 16 + i * 6, 20)}>
                <rect x={x + 30} y={300} width={110} height={110} rx={10} fill="#F1F5F9" />
                <text x={x + 85} y={340} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22} fill="#0F172A">
                  CV
                </text>
                {[0, 1, 2].map((k) => (
                  <rect key={k} x={x + 44} y={355 + k * 14} width={80 - k * 12} height={6} rx={3} fill="#CBD5E1" />
                ))}
              </g>
              <text x={x + 2} y={420} textAnchor="middle" fontFamily={MONO} fontSize={26} fill={C.tenue} opacity={prog(frame, 20, 20)}>
                vs
              </text>
              <Escritorio x={x + 40} y={780} color={C.groq} brillo={pensando ? 1 : 0.4} t={frame + i * 20} />
              <Trabajador x={x - 70} y={850} t={frame + i * 23} tipo="groq" accion={pensando ? "teclear" : listo >= 1 ? "celebrar" : "quieto"} />
              {pensando && (
                <g transform={`translate(${x - 70} 600)`}>
                  {[0, 1, 2].map((k) => (
                    <circle key={k} cx={-24 + k * 24} cy={0} r={7} fill={C.groq} opacity={0.3 + 0.7 * Math.max(0, Math.sin(frame * 0.25 - k))} />
                  ))}
                </g>
              )}
              <g opacity={listo}>
                <Medidor x={x + 10} y={560} valor={o.llm ?? 0} a={listo} />
              </g>
            </g>
          );
        })}
      </Lienzo>
      {CANDIDATAS.map((o, i) => (
        <div key={o.url} style={{ position: "absolute", left: 380 + i * 580 - 230, width: 480, top: 900, display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", opacity: prog(frame, fin[i] + 14, 20) }}>
          {(o.fortalezas ?? []).slice(0, 2).map((f) => (
            <Chip key={f} color={C.verde} style={{ fontSize: 17 }}>
              {f}
            </Chip>
          ))}
        </div>
      ))}
      <div style={{ position: "absolute", right: 120, top: 100, textAlign: "right", fontFamily: MONO, fontSize: 21, color: C.tenue, lineHeight: 1.6, opacity: prog(frame, 200, 24) }}>
        tiempos reales: {datos.evaluador.map((e) => seg(e.seg)).join(" · ")}
        <br />
        {miles(datos.evaluador.reduce((s, e) => s + e.tokens, 0))} tokens · salida estructurada (Pydantic)
      </div>
    </AbsoluteFill>
  );
};

// =====================================================================
// 6. Priorizar: 60 % LLM + 40 % mercado
// =====================================================================
export const Priorizar: React.FC = () => {
  const frame = useCurrentFrame();
  const orden = [...CANDIDATAS].sort((a, b) => (b.final ?? 0) - (a.final ?? 0));
  const reordena = prog(frame, 130, 34);
  const ANCHO = 560;
  return (
    <AbsoluteFill>
      <Fondo acento={C.cian} />
      <Encabezado etiqueta="4 · priorizar" titulo="60 % criterio del LLM + 40 % mercado" color={C.cian} />
      <Lienzo>
        <Trabajador x={230} y={860} t={frame} tipo="bot" accion={frame < 130 ? "leer" : "saludar"} escala={1.05} />
      </Lienzo>
      {CANDIDATAS.map((o, i) => {
        const j = orden.indexOf(o);
        const y = 330 + (i + (j - i) * reordena) * 190;
        const a = prog(frame, 10 + i * 8, 24);
        const b1 = prog(frame, 30 + i * 8, 40);
        const b2 = prog(frame, 60 + i * 8, 40);
        const total = prog(frame, 100 + i * 6, 24);
        return (
          <div key={o.url} style={{ position: "absolute", left: 470, top: y, width: 1330, opacity: a }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, color: C.texto }}>
              {o.titulo} <span style={{ color: C.tenue, fontWeight: 400, fontSize: 24 }}>· {o.empresa}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 24, marginTop: 14 }}>
              <div style={{ width: ANCHO, display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ height: 18, width: ANCHO * 0.6 * ((o.llm ?? 0) / 100) * b1, background: C.groq, borderRadius: 9 }} />
                  <span style={{ fontFamily: MONO, fontSize: 20, color: C.groq, opacity: b1 }}>LLM {o.llm}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ height: 18, width: ANCHO * 0.4 * ((o.mercado ?? 0) / 100) * b2, background: C.cian, borderRadius: 9 }} />
                  <span style={{ fontFamily: MONO, fontSize: 20, color: C.cian, opacity: b2 }}>mercado {o.mercado}</span>
                </div>
              </div>
              <div style={{ fontFamily: MONO, fontSize: 24, color: C.tenue, opacity: total }}>→</div>
              <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 76, color: j === 0 && reordena > 0.5 ? C.verde : C.texto, opacity: total, letterSpacing: -2 }}>{Math.round((o.final ?? 0) * total)}</div>
            </div>
          </div>
        );
      })}
      <Pie desde={170}>Mercado = experiencia pedida, postulantes, antigüedad e inglés. Solo las que superan el umbral pasan al taller de cartas.</Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 7. Taller de cartas: redactor ⇄ revisor
// =====================================================================
const VERIFICADAS = ["people detection and counting system using YOLO models", "Power Automate and SharePoint", "Applied Mathematics and Computer Science"];

export const Taller: React.FC = () => {
  const frame = useCurrentFrame();
  const texto = [datos.carta.cuerpo[0], datos.carta.cuerpo[1], datos.carta.cuerpo[2]].join("\n\n");
  const escritos = Math.floor(lerp(frame, 30, 210, 0, texto.length));
  const visible = texto.slice(0, escritos);
  const revisa = frame > 150;
  const aprobada = prog(frame, 250, 20);

  // resalta las afirmaciones que ya están escritas
  const partes: React.ReactNode[] = [];
  let resto = visible;
  let clave = 0;
  while (resto.length) {
    let primero = -1;
    let frase = "";
    for (const v of VERIFICADAS) {
      const k = resto.indexOf(v);
      if (k >= 0 && (primero < 0 || k < primero)) {
        primero = k;
        frase = v;
      }
    }
    if (primero < 0) {
      partes.push(resto);
      break;
    }
    partes.push(resto.slice(0, primero));
    const orden = VERIFICADAS.indexOf(frase);
    const marca = prog(frame, 160 + orden * 26, 16);
    partes.push(
      <span key={clave++} style={{ background: `rgba(52,211,153,${0.28 * marca})`, boxShadow: marca > 0 ? `inset 0 -2px 0 rgba(52,211,153,${marca})` : undefined, borderRadius: 3 }}>
        {frase}
        {marca > 0.5 && <span style={{ color: "#059669", fontWeight: 700 }}> ✓</span>}
      </span>,
    );
    resto = resto.slice(primero + frase.length);
  }

  return (
    <AbsoluteFill>
      <Fondo acento={C.groq} />
      <Encabezado etiqueta="5 · subgrafo redactor ⇄ revisor" titulo="La carta solo dice lo que dice tu hoja de vida" color={C.groq} />
      <Lienzo>
        <Escritorio x={260} y={800} color={C.groq} brillo={frame < 215 ? 1 : 0.4} t={frame} />
        <Trabajador x={150} y={870} t={frame} tipo="groq" accion={frame < 215 ? "teclear" : "quieto"} />
        <text x={200} y={930} textAnchor="middle" fontFamily={MONO} fontSize={20} fill={C.tenue}>
          redactor
        </text>
        <Trabajador x={1730} y={870} t={frame + 40} tipo="groq" accion={revisa && aprobada < 1 ? "lupa" : aprobada >= 1 ? "saludar" : "quieto"} mira={-1} />
        <text x={1730} y={930} textAnchor="middle" fontFamily={MONO} fontSize={20} fill={C.tenue}>
          revisor
        </text>
        <Globo x={1730} y={630} texto={aprobada > 0 ? "aprobada" : "¿cita en el PDF?"} color={aprobada > 0 ? C.verde : C.groq} a={prog(frame, 150, 14)} />
        {/* ciclo: si inventa algo, vuelve al redactor */}
        <path d="M1640,980 Q960,1050 300,980" fill="none" stroke="rgba(244,63,94,0.45)" strokeWidth={2.5} strokeDasharray="8 8" opacity={prog(frame, 60, 20)} />
        <text x={960} y={1040} textAnchor="middle" fontFamily={MONO} fontSize={19} fill={C.rosa} opacity={prog(frame, 60, 20)}>
          si una frase no tiene cita real, vuelve al redactor (hasta 3 veces)
        </text>
      </Lienzo>
      <div
        style={{
          position: "absolute",
          left: 440,
          top: 250,
          width: 1040,
          height: 640,
          background: "#F8FAFC",
          borderRadius: 14,
          padding: "30px 40px",
          boxShadow: "0 40px 90px rgba(0,0,0,0.55)",
          opacity: prog(frame, 6, 20),
          translate: `0 ${(1 - prog(frame, 6, 24)) * 40}px`,
          overflow: "hidden",
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 17, color: "#64748B", marginBottom: 14 }}>ASUNTO: {datos.carta.asunto}</div>
        <div style={{ fontFamily: SANS, fontSize: 21, lineHeight: 1.5, color: "#0F172A", whiteSpace: "pre-wrap" }}>
          {partes}
          {escritos < texto.length && <span style={{ display: "inline-block", width: 10, height: 24, background: C.groq, translate: "0 4px" }} />}
        </div>
        <div
          style={{
            position: "absolute",
            right: 40,
            bottom: 26,
            fontFamily: MONO,
            fontWeight: 700,
            fontSize: 26,
            color: "#059669",
            border: "3px solid #059669",
            padding: "4px 16px",
            borderRadius: 8,
            rotate: "-8deg",
            opacity: aprobada,
            scale: String(1.6 - 0.6 * aprobada),
          }}
        >
          APROBADA · intento 1 de 3
        </div>
      </div>
      <div style={{ position: "absolute", right: 120, top: 100, textAlign: "right", fontFamily: MONO, fontSize: 21, color: C.tenue, lineHeight: 1.6, opacity: prog(frame, 270, 24) }}>
        3 cartas · 3 aprobadas al primer intento
        <br />
        {datos.taller.map((e) => seg(e.seg)).join(" · ")} · {miles(datos.taller.reduce((s, e) => s + e.tokens, 0))} tokens
      </div>
    </AbsoluteFill>
  );
};

// =====================================================================
// 8. Resumen y aprobación humana
// =====================================================================
export const Aprobacion: React.FC = () => {
  const frame = useCurrentFrame();
  const vuelo = prog(frame, 30, 40);
  const comando = "python main.py --aprobar 2,3";
  const tecleado = comando.slice(0, Math.floor(lerp(frame, 150, 200, 0, comando.length)));
  const ok = prog(frame, 210, 16);
  const cola = [...CANDIDATAS].sort((a, b) => Number(a.id) - Number(b.id));
  return (
    <AbsoluteFill>
      <Fondo acento={C.ambar} />
      <Encabezado etiqueta="6 · notificador + humano en el ciclo" titulo="Nada sale sin tu aprobación" color={C.ambar} />
      <Lienzo>
        <Trabajador x={210} y={880} t={frame} tipo="bot" accion={frame < 40 ? "saludar" : "quieto"} />
        <text x={210} y={940} textAnchor="middle" fontFamily={MONO} fontSize={20} fill={C.tenue}>
          notificador
        </text>
        {vuelo > 0 && vuelo < 1 && <Sobre x={290 + vuelo * 1260} y={700 - Math.sin(vuelo * Math.PI) * 260} tam={80} color={C.cian} rot={vuelo * 20 - 10} />}
        <Trabajador x={1700} y={880} t={frame + 30} tipo="humano" accion={ok >= 1 ? "celebrar" : frame > 70 ? "leer" : "quieto"} mira={-1} />
        <text x={1700} y={940} textAnchor="middle" fontFamily={MONO} fontSize={20} fill={C.tenue}>
          tú
        </text>
        {/* el grafo en pausa */}
        <g opacity={prog(frame, 60, 20) * (1 - ok)} transform="translate(1700 600)">
          <circle r={34} fill="rgba(245,165,36,0.15)" stroke={C.ambar} strokeWidth={3} />
          <rect x={-12} y={-14} width={8} height={28} rx={2} fill={C.ambar} />
          <rect x={4} y={-14} width={8} height={28} rx={2} fill={C.ambar} />
        </g>
      </Lienzo>
      <Tarjeta style={{ position: "absolute", left: 420, top: 270, width: 1060, padding: "30px 36px", opacity: prog(frame, 60, 24), translate: `0 ${(1 - prog(frame, 60, 24)) * 30}px` }} color={C.ambar}>
        <div style={{ fontFamily: MONO, fontSize: 19, color: C.ambar, marginBottom: 18 }}>3 postulaciones esperan tu aprobación · interrupt() · estado en SQLite</div>
        {cola.map((o, i) => {
          const elegida = o.id === 2 || o.id === 3;
          const marca = elegida ? prog(frame, 210 + i * 6, 14) : 0;
          return (
            <div key={o.url} style={{ display: "flex", alignItems: "center", gap: 18, padding: "12px 0", borderTop: i ? `1px solid ${C.borde}` : undefined, opacity: prog(frame, 80 + i * 10, 20) }}>
              <span style={{ fontFamily: MONO, fontSize: 24, color: C.tenue, width: 50 }}>#{o.id}</span>
              <span style={{ fontFamily: MONO, fontSize: 24, color: C.verde, width: 60 }}>{o.final}</span>
              <span style={{ fontFamily: SANS, fontSize: 26, color: C.texto, flex: 1 }}>{o.titulo}</span>
              <span style={{ fontFamily: MONO, fontSize: 19, color: C.tenue }}>{o.correo ? "correo" : "portal (manual)"}</span>
              <span style={{ width: 34, height: 34, borderRadius: 8, border: `2px solid ${marca > 0 ? C.verde : C.borde}`, display: "flex", alignItems: "center", justifyContent: "center", color: C.verde, fontSize: 24, background: `rgba(52,211,153,${0.15 * marca})` }}>{marca > 0.5 ? "✓" : ""}</span>
            </div>
          );
        })}
      </Tarjeta>
      <div style={{ position: "absolute", left: 420, top: 640, width: 1060, padding: "20px 28px", borderRadius: 16, background: "#0A0F1A", border: `1px solid ${C.borde}`, fontFamily: MONO, fontSize: 26, color: C.texto, opacity: prog(frame, 140, 16) }}>
        <span style={{ color: C.verde }}>$ </span>
        {tecleado}
        {tecleado.length < comando.length && <span style={{ display: "inline-block", width: 12, height: 26, background: C.texto, translate: "0 4px", opacity: Math.floor(frame / 8) % 2 }} />}
        <div style={{ fontSize: 20, color: C.tenue, marginTop: 10, opacity: ok }}>Command(resume=[2, 3]) · el grafo sigue donde se quedó, aunque sea otro proceso</div>
      </div>
    </AbsoluteFill>
  );
};

// =====================================================================
// 9. Postulador
// =====================================================================
export const Postulador: React.FC = () => {
  const frame = useCurrentFrame();
  const camina = prog(frame, 10, 70);
  const x = 260 + camina * 820;
  const envios = CANDIDATAS.filter((o) => o.correo).sort((a, b) => Number(a.id) - Number(b.id));
  const manual = CANDIDATAS.find((o) => !o.correo);
  return (
    <AbsoluteFill>
      <Fondo acento={C.verde} />
      <Encabezado etiqueta="7 · agente postulador" titulo="Carta + hoja de vida, en el idioma de la oferta" color={C.verde} />
      <Lienzo>
        {/* buzón */}
        <g transform="translate(1320 860)">
          <rect x={-12} y={-160} width={24} height={160} fill="#334155" />
          <rect x={-90} y={-290} width={180} height={140} rx={30} fill={C.verde} opacity={0.9} />
          <rect x={-60} y={-250} width={120} height={14} rx={7} fill="#064E3B" />
          <rect x={86} y={-290} width={10} height={70} fill={C.rosa} transform={`rotate(${prog(frame, 120, 16) * -70} 91 -220)`} />
        </g>
        {envios.map((o, i) => {
          const v = prog(frame, 90 + i * 22, 26);
          if (v >= 1) return null;
          const sx = x + 60;
          const sy = 700 - i * 30;
          return <Sobre key={o.url} x={sx + (1320 - sx) * v} y={sy + (604 - sy) * v - Math.sin(v * Math.PI) * 120} tam={70} rot={v * 30} opacidad={1 - v * 0.6} />;
        })}
        <Trabajador x={x} y={860} t={frame} tipo="bot" accion={camina < 1 ? "cargar" : frame < 150 ? "quieto" : "saludar"} />
      </Lienzo>
      <div style={{ position: "absolute", left: 1480, top: 360, width: 360, display: "flex", flexDirection: "column", gap: 18 }}>
        {envios.map((o, i) => (
          <div key={o.url} style={{ opacity: prog(frame, 116 + i * 22, 20) }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: C.texto }}>
              #{o.id} · {o.empresa}
            </div>
            <div style={{ fontFamily: MONO, fontSize: 18, color: C.verde }}>
              {o.idioma === "en" ? "en inglés" : "en español"} · {datos.postulaciones.find((p) => p.id === o.id)?.estado}
            </div>
          </div>
        ))}
        {manual && (
          <div style={{ opacity: prog(frame, 170, 20) }}>
            <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: C.texto }}>
              #{manual.id} · {manual.empresa}
            </div>
            <div style={{ fontFamily: MONO, fontSize: 18, color: C.tenue }}>sin correo: carta lista + enlace al portal</div>
          </div>
        )}
      </div>
      <Pie desde={150}>En la demo los correos usan el dominio reservado .invalid: el envío queda «simulado» y nunca llega a nadie.</Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 10. Métricas
// =====================================================================
export const Metricas: React.FC = () => {
  const frame = useCurrentFrame();
  const ev = datos.evaluador.reduce((s, e) => s + e.tokens, 0);
  const ta = datos.taller.reduce((s, e) => s + e.tokens, 0);
  const barras = [
    { nombre: "redactor ⇄ revisor", v: ta, color: C.groq },
    { nombre: "evaluador", v: ev, color: C.groq },
    { nombre: "buscador · filtro · priorizar · notificador · postulador", v: 0, color: C.cian },
  ];
  return (
    <AbsoluteFill>
      <Fondo acento={C.cian} />
      <Encabezado etiqueta="resultados medidos" titulo="Cuánto tarda y cuánto cuesta" color={C.cian} />
      <Tarjeta style={{ position: "absolute", left: 120, top: 280, width: 800, height: 600, padding: 44 }}>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.tenue }}>15 portales · corrida diaria real</div>
        {[
          { n: "versión 1 · script en fila", s: 278, txt: "4 min 38 s", c: C.tenue },
          { n: "versión 2 · LangGraph en paralelo", s: 76, txt: "1 min 16 s", c: C.cian },
        ].map((b, i) => {
          const a = prog(frame, 20 + i * 20, 50);
          return (
            <div key={b.n} style={{ marginTop: 50 }}>
              <div style={{ fontFamily: SANS, fontSize: 26, color: C.texto }}>{b.n}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 12 }}>
                <div style={{ height: 34, width: (b.s / 278) * 420 * a, background: b.c, borderRadius: 10 }} />
                <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 36, color: b.c, opacity: a }}>{b.txt}</span>
              </div>
            </div>
          );
        })}
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 64, color: C.texto, marginTop: 60, opacity: prog(frame, 80, 30) }}>
          3,7× <span style={{ fontSize: 28, fontWeight: 400, color: C.tenue }}>más rápido · {miles(1354)} ofertas</span>
        </div>
      </Tarjeta>
      <Tarjeta style={{ position: "absolute", left: 1000, top: 280, width: 800, height: 600, padding: 44 }}>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.tenue }}>tokens por agente · demo con 3 cartas</div>
        {barras.map((b, i) => {
          const a = prog(frame, 40 + i * 18, 50);
          return (
            <div key={b.nombre} style={{ marginTop: 40 }}>
              <div style={{ fontFamily: SANS, fontSize: 24, color: C.texto }}>{b.nombre}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 10 }}>
                <div style={{ height: 30, width: Math.max(6, (b.v / ta) * 470 * a), background: b.color, borderRadius: 9, opacity: b.v ? 1 : 0.5 }} />
                <span style={{ fontFamily: MONO, fontSize: 26, color: b.v ? C.texto : C.tenue, opacity: a }}>{miles(Math.round(b.v * a))}</span>
              </div>
            </div>
          );
        })}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 50, opacity: prog(frame, 110, 30) }}>
          <svg width={44} height={44}>
            <circle cx={22} cy={22} r={22} fill={C.groq} />
            <LogoGroq x={22} y={22} tam={30} />
          </svg>
          <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: C.texto }}>{miles(datos.tokens_total)}</span>
          <span style={{ fontFamily: SANS, fontSize: 26, color: C.tenue }}>tokens en total · plan gratuito</span>
        </div>
      </Tarjeta>
      <Pie desde={150}>7 pruebas con un modelo falso cubren el flujo, el ciclo de revisión, las citas, la pausa y la reanudación.</Pie>
    </AbsoluteFill>
  );
};

// =====================================================================
// 11. Cierre
// =====================================================================
export const Cierre: React.FC = () => {
  const frame = useCurrentFrame();
  const a = prog(frame, 0, 30);
  return (
    <AbsoluteFill>
      <Fondo acento={C.groq} />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 220 }}>
        <div style={{ overflow: "hidden", paddingBottom: 10 }}>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 100, letterSpacing: -3.5, color: C.texto, translate: `0 ${(1 - a) * 130}px` }}>Agente de Empleo</div>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 28, color: C.groq, opacity: prog(frame, 14, 30), marginTop: 10 }}>LangGraph · Groq · Pydantic · SQLite · humano en el ciclo</div>
        <div style={{ fontFamily: MONO, fontSize: 24, color: C.tenue, opacity: prog(frame, 26, 30), marginTop: 36, padding: "12px 28px", border: `1px solid ${C.borde}`, borderRadius: 999 }}>github.com/CARLYGP/Agente_Empleo_LangGraph</div>
      </AbsoluteFill>
      <Lienzo>
        {EQUIPO.map((e, i) => (
          <Trabajador key={i} x={330 + i * 180} y={980} t={frame + i * 13} tipo={e.tipo} accion={i % 2 ? "saludar" : "celebrar"} escala={0.8} opacidad={prog(frame, 10 + i * 4, 20)} />
        ))}
      </Lienzo>
    </AbsoluteFill>
  );
};
