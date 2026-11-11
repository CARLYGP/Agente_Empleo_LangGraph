import React from "react";
import { AbsoluteFill, Composition, Still } from "remotion";
import { TransitionSeries, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { Aprobacion, Buscadores, Cierre, Equipo, Evaluadores, Filtro, Intro, Metricas, Postulador, Priorizar, Taller } from "./escenas";
import { Lienzo, Trabajador, Tipo } from "./personajes";
import { PERIODO, TarjetaAgente } from "./Tarjeta";
import { C, Fondo, MONO, SANS } from "./tema";

const T = 20;
const ESCENAS: [string, React.FC, number][] = [
  ["Portada", Intro, 150],
  ["Equipo", Equipo, 230],
  ["Buscadores", Buscadores, 240],
  ["Filtro", Filtro, 240],
  ["Evaluadores", Evaluadores, 290],
  ["Priorizar", Priorizar, 220],
  ["Taller", Taller, 320],
  ["Aprobación", Aprobacion, 290],
  ["Postulador", Postulador, 220],
  ["Métricas", Metricas, 230],
  ["Cierre", Cierre, 150],
];
const DURACION = ESCENAS.reduce((s, e) => s + e[2], 0) - T * (ESCENAS.length - 1);

export const AgenteVideo: React.FC = () => (
  <TransitionSeries>
    {ESCENAS.flatMap(([nombre, Escena, dur], i) => {
      const nodos = [
        <TransitionSeries.Sequence key={nombre} name={nombre} durationInFrames={dur}>
          <Escena />
        </TransitionSeries.Sequence>,
      ];
      if (i < ESCENAS.length - 1)
        nodos.push(
          <TransitionSeries.Transition
            key={nombre + "-t"}
            presentation={(i % 2 === 0 ? fade() : slide({ direction: "from-right" })) as ReturnType<typeof fade>}
            timing={springTiming({ config: { damping: 200 }, durationInFrames: T })}
          />,
        );
      return nodos;
    })}
  </TransitionSeries>
);

const BANDA: { tipo: Tipo; accion: "teclear" | "leer" | "lupa" | "saludar" | "sellar" | "quieto" }[] = [
  { tipo: "bot", accion: "sellar" },
  { tipo: "groq", accion: "leer" },
  { tipo: "groq", accion: "teclear" },
  { tipo: "groq", accion: "lupa" },
  { tipo: "humano", accion: "saludar" },
];

export const PortadaBanner: React.FC = () => (
  <AbsoluteFill>
    <Fondo acento={C.groq} />
    <div style={{ position: "absolute", left: 90, top: 150 }}>
      <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 4, color: C.groq, textTransform: "uppercase" }}>LangGraph · Groq · humano en el ciclo</div>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 84, lineHeight: 1.02, letterSpacing: -3, color: C.texto, marginTop: 14 }}>
        Un equipo de agentes
        <br />
        que busca empleo por ti
      </div>
      <div style={{ fontFamily: SANS, fontSize: 28, color: C.tenue, marginTop: 22 }}>15 portales · evaluación con LLM · cartas verificadas · tú apruebas</div>
    </div>
    <Lienzo w={1600} h={640}>
      {BANDA.map((b, i) => (
        <Trabajador key={i} x={1095 + i * 112} y={600 - (i % 2) * 34} t={20 + i * 9} tipo={b.tipo} accion={b.accion} escala={0.7} />
      ))}
    </Lienzo>
  </AbsoluteFill>
);

export const Composiciones: React.FC = () => (
  <>
    <Composition id="AgenteEmpleo" component={AgenteVideo} durationInFrames={DURACION} fps={30} width={1920} height={1080} />
    <Still id="PortadaBanner" component={PortadaBanner} width={1600} height={640} />
    <Composition id="TarjetaAgente" component={TarjetaAgente} durationInFrames={PERIODO} fps={30} width={800} height={600} />
  </>
);
