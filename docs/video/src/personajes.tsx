import React from "react";
import { C, MONO } from "./tema";

/** Trabajadores del grafo: robots Groq (agentes con LLM), robots cian (nodos deterministas) y la persona (tú). */

export const GROQ =
  "M12.036 2c-3.853-.035-7 3-7.036 6.781-.035 3.782 3.055 6.872 6.908 6.907h2.42v-2.566h-2.292c-2.407.028-4.38-1.866-4.408-4.23-.029-2.362 1.901-4.298 4.308-4.326h.1c2.407 0 4.358 1.915 4.365 4.278v6.305c0 2.342-1.944 4.25-4.323 4.279a4.375 4.375 0 01-3.033-1.252l-1.851 1.818A7 7 0 0012.029 22h.092c3.803-.056 6.858-3.083 6.879-6.816v-6.5C18.907 4.963 15.817 2 12.036 2z";

export const LogoGroq: React.FC<{ x: number; y: number; tam: number; color?: string }> = ({ x, y, tam, color = "#fff" }) => (
  <path d={GROQ} fill={color} transform={`translate(${x - tam / 2} ${y - tam / 2}) scale(${tam / 24})`} />
);

export type Tipo = "groq" | "bot" | "humano";
export type Accion = "quieto" | "teclear" | "caminar" | "sellar" | "leer" | "lupa" | "saludar" | "cargar" | "celebrar";

const PIEL = "#E9B48C";

/** Brazo con codo: ángulos en grados medidos desde la vertical hacia abajo (positivo = hacia adelante). */
const Brazo: React.FC<{ hx: number; hy: number; a1: number; a2: number; color: string; mano: string }> = ({ hx, hy, a1, a2, color, mano }) => {
  const r = (g: number) => (g * Math.PI) / 180;
  const ex = hx + Math.sin(r(a1)) * 30;
  const ey = hy + Math.cos(r(a1)) * 30;
  const mx = ex + Math.sin(r(a1 + a2)) * 28;
  const my = ey + Math.cos(r(a1 + a2)) * 28;
  return (
    <g>
      <path d={`M${hx},${hy} L${ex},${ey} L${mx},${my}`} stroke={color} strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <circle cx={mx} cy={my} r={8} fill={mano} />
    </g>
  );
};

/**
 * Un trabajador con los pies en (x, y). `t` es el frame (o un frame desplazado para desincronizar).
 * `mira` = 1 mira a la derecha, -1 a la izquierda.
 */
export const Trabajador: React.FC<{
  x: number;
  y: number;
  t: number;
  tipo: Tipo;
  accion?: Accion;
  escala?: number;
  mira?: 1 | -1;
  color?: string;
  objeto?: React.ReactNode; // algo en las manos (hoja, sobre...)
  opacidad?: number;
}> = ({ x, y, t, tipo, accion = "quieto", escala = 1, mira = 1, color, objeto, opacidad = 1 }) => {
  const base = color ?? (tipo === "groq" ? C.groq : tipo === "bot" ? "#2B3A55" : "#3B4A6B");
  const camina = accion === "caminar" || accion === "cargar";
  const bob = camina ? Math.abs(Math.sin(t * 0.32)) * -5 : accion === "celebrar" ? Math.abs(Math.sin(t * 0.25)) * -16 : Math.sin(t * 0.07) * 1.6;
  const parpadeo = t % 97 < 4 ? 0.15 : 1;

  // ángulos de brazos según la acción [hombro, codo] para el brazo de atrás (izq) y el de adelante (der)
  let atras: [number, number] = [8, 6];
  let adelante: [number, number] = [-8, -6];
  const s = Math.sin;
  switch (accion) {
    case "teclear":
      atras = [62 + s(t * 0.9) * 7, 38];
      adelante = [58 + s(t * 0.9 + 2) * 7, 42];
      break;
    case "caminar":
      atras = [s(t * 0.32) * 28, 10];
      adelante = [-s(t * 0.32) * 28, 10];
      break;
    case "cargar":
      atras = [70, 55];
      adelante = [74, 50];
      break;
    case "sellar": {
      const g = (t % 36) / 36;
      const golpe = g < 0.5 ? g * 2 : 2 - g * 2;
      atras = [30, 40];
      adelante = [100 - golpe * 70, 30 - golpe * 20];
      break;
    }
    case "leer":
      atras = [55, 60];
      adelante = [60, 55];
      break;
    case "lupa":
      atras = [40, 40];
      adelante = [95 + s(t * 0.12) * 12, 40];
      break;
    case "saludar":
      atras = [6, 6];
      adelante = [160, 10 + s(t * 0.35) * 25];
      break;
    case "celebrar":
      atras = [-150, -10];
      adelante = [150, 10];
      break;
  }
  const pierna = camina ? s(t * 0.32) * 24 : 0;

  const piel = tipo === "humano" ? PIEL : tipo === "groq" ? "#FFB39F" : "#9FB3D1";
  const manga = tipo === "humano" ? "#E5E7EB" : base;

  return (
    <g transform={`translate(${x} ${y}) scale(${escala * mira} ${escala})`} opacity={opacidad}>
      <ellipse cx={0} cy={2} rx={42} ry={8} fill="rgba(0,0,0,0.45)" />
      <g transform={`translate(0 ${bob})`}>
        {/* piernas */}
        {[pierna, -pierna].map((a, i) => (
          <g key={i} transform={`rotate(${a} ${i ? 10 : -10} -52)`}>
            <rect x={(i ? 10 : -10) - 8} y={-54} width={16} height={52} rx={8} fill={tipo === "humano" ? "#1F2A44" : "#1A2336"} />
          </g>
        ))}
        {/* brazo de atrás */}
        <Brazo hx={-20} hy={-112} a1={atras[0]} a2={atras[1]} color={manga} mano={piel} />
        {/* torso */}
        <path d="M-34,-122 Q-36,-50 -26,-48 L26,-48 Q36,-50 34,-122 Q0,-134 -34,-122 Z" fill={tipo === "humano" ? "#E5E7EB" : base} />
        {tipo === "groq" && (
          <g>
            <circle cx={0} cy={-88} r={15} fill="#fff" />
            <LogoGroq x={0} y={-88} tam={22} color={C.groq} />
          </g>
        )}
        {tipo === "bot" && <circle cx={0} cy={-90} r={7} fill={C.cian} opacity={0.6 + 0.4 * Math.sin(t * 0.2)} />}
        {tipo === "humano" && <path d="M-12,-126 L0,-110 L12,-126" fill="none" stroke="#94A3B8" strokeWidth={3} />}
        {/* cabeza */}
        {tipo === "humano" ? (
          <g>
            <rect x={-8} y={-136} width={16} height={14} fill={PIEL} />
            <circle cx={0} cy={-160} r={28} fill={PIEL} />
            <path d="M-29,-160 Q-30,-196 2,-192 Q30,-192 28,-162 Q22,-178 2,-178 Q-18,-176 -29,-160 Z" fill="#2A1E17" />
            <ellipse cx={-9} cy={-160} rx={3.2} ry={3.6 * parpadeo} fill="#1F2937" />
            <ellipse cx={11} cy={-160} rx={3.2} ry={3.6 * parpadeo} fill="#1F2937" />
            <path d="M-6,-147 Q2,-141 10,-147" stroke="#7C2D12" strokeWidth={2.4} fill="none" strokeLinecap="round" />
          </g>
        ) : (
          <g>
            <line x1={0} y1={-190} x2={0} y2={-206} stroke={tipo === "groq" ? C.groq : "#5B6B88"} strokeWidth={4} />
            <circle cx={0} cy={-209} r={6} fill={tipo === "groq" ? C.groq : C.cian} opacity={0.5 + 0.5 * Math.abs(Math.sin(t * 0.15))} />
            <rect x={-34} y={-192} width={68} height={58} rx={18} fill={tipo === "groq" ? C.groq : "#33445F"} />
            <rect x={-26} y={-183} width={52} height={40} rx={12} fill="#0B1220" />
            <rect x={-16} y={-171} width={9} height={14 * parpadeo} rx={4.5} fill={tipo === "groq" ? "#FFD8CC" : "#9EEBFA"} transform={`translate(0 ${7 * (1 - parpadeo)})`} />
            <rect x={8} y={-171} width={9} height={14 * parpadeo} rx={4.5} fill={tipo === "groq" ? "#FFD8CC" : "#9EEBFA"} transform={`translate(0 ${7 * (1 - parpadeo)})`} />
          </g>
        )}
        {objeto}
        {/* brazo de adelante */}
        <Brazo hx={20} hy={-112} a1={adelante[0]} a2={adelante[1]} color={manga} mano={piel} />
        {accion === "lupa" && (
          <g transform={`translate(${62 + Math.sin(t * 0.12) * 6} ${-150})`}>
            <circle r={18} fill="rgba(158,235,250,0.15)" stroke="#CBD5E1" strokeWidth={5} />
            <line x1={-12} y1={14} x2={-26} y2={30} stroke="#CBD5E1" strokeWidth={6} strokeLinecap="round" />
          </g>
        )}
      </g>
    </g>
  );
};

/** Escritorio con portátil; `brillo` 0..1 enciende la pantalla. */
export const Escritorio: React.FC<{ x: number; y: number; color?: string; brillo?: number; ancho?: number; t?: number }> = ({ x, y, color = C.cian, brillo = 1, ancho = 170, t = 0 }) => (
  <g transform={`translate(${x} ${y})`}>
    <rect x={-ancho / 2} y={-6} width={ancho} height={14} rx={5} fill="#24324D" />
    <rect x={-ancho / 2 + 10} y={8} width={10} height={64} fill="#1A2438" />
    <rect x={ancho / 2 - 20} y={8} width={10} height={64} fill="#1A2438" />
    <g transform="translate(-6 -6)">
      <path d="M-40,0 L40,0 L46,6 L-46,6 Z" fill="#3A4A68" />
      <rect x={-38} y={-58} width={76} height={56} rx={5} fill="#0B1220" stroke="#3A4A68" strokeWidth={3} />
      <rect x={-32} y={-52} width={64} height={44} rx={3} fill={color} opacity={0.18 * brillo} />
      {[0, 1, 2, 3].map((k) => (
        <rect key={k} x={-26} y={-46 + k * 10} width={(30 + ((k * 17 + Math.floor(t / 6)) % 22)) * brillo} height={4} rx={2} fill={color} opacity={0.75 * brillo} />
      ))}
    </g>
  </g>
);

/** Tarjeta de oferta (la hoja que los trabajadores se pasan). */
export const Hoja: React.FC<{ x: number; y: number; ancho?: number; titulo?: string; color?: string; rot?: number; opacidad?: number; sello?: { texto: string; color: string; a: number } }> = ({
  x,
  y,
  ancho = 120,
  titulo,
  color = C.cian,
  rot = 0,
  opacidad = 1,
  sello,
}) => {
  const alto = ancho * 0.72;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`} opacity={opacidad}>
      <rect x={-ancho / 2} y={-alto / 2} width={ancho} height={alto} rx={8} fill="#F1F5F9" />
      <rect x={-ancho / 2} y={-alto / 2} width={ancho} height={8} rx={4} fill={color} />
      {titulo ? (
        <text x={-ancho / 2 + 10} y={-alto / 2 + 30} fontFamily={MONO} fontSize={Math.min(ancho * 0.1, (ancho - 20) / (titulo.length * 0.6))} fill="#0F172A">
          {titulo}
        </text>
      ) : null}
      {[0, 1, 2].map((k) => (
        <rect key={k} x={-ancho / 2 + 10} y={-alto / 2 + (titulo ? 42 : 22) + k * 12} width={ancho * (0.7 - k * 0.15)} height={5} rx={2.5} fill="#CBD5E1" />
      ))}
      {sello && sello.a > 0 && (
        <g transform={`rotate(-14) scale(${1.6 - 0.6 * sello.a})`} opacity={sello.a}>
          <rect x={-ancho * 0.42} y={-15} width={ancho * 0.84} height={30} rx={5} fill="none" stroke={sello.color} strokeWidth={4} />
          <text x={0} y={7} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={ancho * 0.12} fill={sello.color}>
            {sello.texto}
          </text>
        </g>
      )}
    </g>
  );
};

/** Sobre de correo. */
export const Sobre: React.FC<{ x: number; y: number; tam?: number; color?: string; rot?: number; opacidad?: number }> = ({ x, y, tam = 60, color = C.verde, rot = 0, opacidad = 1 }) => (
  <g transform={`translate(${x} ${y}) rotate(${rot})`} opacity={opacidad}>
    <rect x={-tam / 2} y={-tam * 0.33} width={tam} height={tam * 0.66} rx={5} fill="#F1F5F9" />
    <path d={`M${-tam / 2 + 3},${-tam * 0.3} L0,${tam * 0.06} L${tam / 2 - 3},${-tam * 0.3}`} fill="none" stroke={color} strokeWidth={3.5} strokeLinejoin="round" />
  </g>
);

/** Globo de diálogo sobre un trabajador. */
export const Globo: React.FC<{ x: number; y: number; texto: string; color?: string; a: number; tam?: number }> = ({ x, y, texto, color = C.texto, a, tam = 22 }) => {
  if (a <= 0) return null;
  const w = texto.length * tam * 0.62 + 32;
  return (
    <g transform={`translate(${x} ${y}) scale(${0.6 + 0.4 * a})`} opacity={a}>
      <rect x={-w / 2} y={-tam - 22} width={w} height={tam + 24} rx={14} fill="rgba(13,19,34,0.95)" stroke={color} strokeOpacity={0.6} />
      <path d="M-8,1 L0,12 L8,1 Z" fill="rgba(13,19,34,0.95)" />
      <text x={0} y={-12} textAnchor="middle" fontFamily={MONO} fontSize={tam} fill={color}>
        {texto}
      </text>
    </g>
  );
};

/** SVG de escena a pantalla completa, en su propia capa (si no, el Fondo lo tapa). */
export const Lienzo: React.FC<{ children: React.ReactNode; w?: number; h?: number }> = ({ children, w = 1920, h = 1080 }) => (
  <div style={{ position: "absolute", inset: 0 }}>
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: "visible" }}>
      {children}
    </svg>
  </div>
);
