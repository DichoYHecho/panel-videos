/**
 * Vídeo largo «¿Quién lo dijo? · El gran quiz de las frases» (horizontal 1920x1080, 30 fps). Prototipo.
 * Estilo limpio tipo Apple: fondo negro con luces de color suaves y desenfocadas (el color del nivel),
 * paneles de cristal esmerilado, tipografía sin serifa grande y mucho aire. Las frases, en serifa.
 * Intro → niveles (Fácil, Medio, Difícil, Experto) con cortinilla → preguntas → final con puntuación.
 * Cada pregunta: planteamiento, opciones, reloj de 5 s, revelación (✓/✕) y «¿Lo sabías?».
 * Tipos: quien, completa, vf, pais (con banderas), siglo (con el retrato), pistas.
 * Música variada: una pista por tramo (intro, cada nivel, final), creada con código.
 * Todo lo que se afirma sale del banco verificado de citas y de Wikidata.
 */
import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {AMARILLO, FPS, INTER, ROJO, Suscribete, VERDE, lerp, pop, rampa} from './base';
import {CitaPluma, Comillas, LineaVida, MapaPais, Opciones, type Opcion, type Pais} from './piezas';

const W = 1920;
const H = 1080;
export const NIVELES = [
	{nombre: 'Fácil', color: '#34C759'},
	{nombre: 'Medio', color: '#0A84FF'},
	{nombre: 'Difícil', color: '#FF9F0A'},
	{nombre: 'Experto', color: '#FF375F'},
];
const GRIS = '#a1a1a6';
/** Momentos (s) de cada fase de una pregunta. Con narración los calcula quiz_largo.py según lo que dura la voz. */
type Tiempos = {pregunta: number; opciones: number; reloj: number; rev: number; dato: number; fin: number; vozA?: number; vozB?: number; cita?: [number, number]; pistas?: number[]};
const T_FIJO: Tiempos = {pregunta: 0.4, opciones: 2.2, reloj: 3.6, rev: 8.6, dato: 9.4, fin: 13};
const INTRO = 6;
const CORTINILLA = 2.6;
const FINAL = 9;

type Ficha = {autor: string; foto: string; foco: [number, number]; dato: string};
export type Pregunta = {nivel: number; ficha: Ficha; T?: Tiempos; voz?: {a: string; b: string}} & (
	| {tipo: 'quien'; cita: string; opciones: Opcion[]; correcta: number}
	| {tipo: 'completa'; antes: string; opciones: string[]; correcta: number}
	| {tipo: 'vf'; cita: string; propuesto: Opcion; verdadero: boolean}
	| {tipo: 'pais'; paises: Pais[]; correcta: number}
	| {tipo: 'siglo'; opciones: {rotulo: string; desde: number; hasta: number}[]; correcta: number; vida: {nace: number; muere: number}}
	| {tipo: 'pistas'; pistas: {icono: string; texto: string}[]; recorte: string | null; proporcion: number}
);
export type DatosQuizLargo = {
	titulo: string;
	subtitulo: string;
	total: number;
	preguntas: Pregunta[];
	musica: {intro: string; niveles: string[]; final: string};
	/** narración (opcional): intro, frase de cada nivel y final */
	voces?: {intro: string; niveles: string[]; final: string};
	duraciones?: {intro: number; cortinilla: number[]; final: number};
};
const tiemposDe = (p: Pregunta): Tiempos => p.T ?? T_FIJO;

const ROTULO_TIPO: Record<Pregunta['tipo'], string> = {
	quien: '¿Quién lo dijo?',
	completa: 'Completa la frase',
	vf: '¿Verdadero o falso?',
	pais: '¿De qué país era?',
	siglo: '¿En qué siglo vivió?',
	pistas: 'Adivina por pistas',
};

/** Línea de tiempo del vídeo: intro, cortinilla al empezar cada nivel, preguntas, final. */
const plan = (d: DatosQuizLargo) => {
	const intro = d.duraciones?.intro ?? INTRO;
	const fin = d.duraciones?.final ?? FINAL;
	const pasos: {tipo: 'intro' | 'nivel' | 'pregunta' | 'final'; desde: number; dur: number; i?: number}[] = [{tipo: 'intro', desde: 0, dur: intro}];
	const tramos: {nivel: number; desde: number; hasta: number}[] = [];
	let t = intro;
	let nivel = -1;
	d.preguntas.forEach((p, i) => {
		if (p.nivel !== nivel) {
			if (tramos.length) tramos[tramos.length - 1].hasta = t;
			nivel = p.nivel;
			tramos.push({nivel, desde: t, hasta: t});
			const c = d.duraciones?.cortinilla[tramos.length - 1] ?? CORTINILLA;
			pasos.push({tipo: 'nivel', desde: t, dur: c, i});
			t += c;
		}
		const f = tiemposDe(p).fin;
		pasos.push({tipo: 'pregunta', desde: t, dur: f, i});
		t += f;
	});
	if (tramos.length) tramos[tramos.length - 1].hasta = t;
	pasos.push({tipo: 'final', desde: t, dur: fin});
	return {pasos, tramos, dur: t + fin};
};
export const duracionQuizLargo = (d: DatosQuizLargo) => Math.round(plan(d).dur * FPS);

// ---------------------------------------------------------------- estilo
const cristal: React.CSSProperties = {
	background: 'rgba(255,255,255,0.07)',
	border: '1px solid rgba(255,255,255,0.14)',
	backdropFilter: 'blur(24px)',
	WebkitBackdropFilter: 'blur(24px)',
	boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
};
const titular: React.CSSProperties = {fontFamily: INTER, fontWeight: 800, letterSpacing: -1.5, color: '#f5f5f7'};
/** Texto con degradado (blanco → gris), como en las presentaciones de Apple. */
const degradado = (de = '#ffffff', a = '#9a9aa0'): React.CSSProperties => ({
	backgroundImage: `linear-gradient(180deg, ${de} 20%, ${a} 100%)`,
	WebkitBackgroundClip: 'text',
	backgroundClip: 'text',
	color: 'transparent',
});

/** Fondo negro con dos luces de color grandes y desenfocadas que se mueven despacio. */
const Fondo: React.FC<{t: number; color: string}> = ({t, color}) => {
	const a = Math.sin(t * 0.15);
	const b = Math.cos(t * 0.11);
	return (
		<AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
			<div style={{position: 'absolute', width: 1300, height: 1300, borderRadius: '50%', left: 900 + 160 * a, top: -500 + 120 * b, background: color, opacity: 0.32, filter: 'blur(200px)'}} />
			<div style={{position: 'absolute', width: 1100, height: 1100, borderRadius: '50%', left: -400 + 140 * b, top: 400 + 100 * a, background: '#5E5CE6', opacity: 0.22, filter: 'blur(220px)'}} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 70% at 50% 50%, transparent 40%, rgba(0,0,0,0.6) 100%)'}} />
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- cabecera: nivel, marcador, tipo
const Cabecera: React.FC<{nivel: number; actual: number; total: number; tipo: string; t: number; resuelta: boolean}> = ({nivel, actual, total, tipo, t, resuelta}) => {
	const n = NIVELES[nivel];
	return (
		<div style={{position: 'absolute', top: 40, left: 64, right: 64, height: 72, display: 'flex', alignItems: 'center', justifyContent: 'space-between', opacity: rampa(t, 0, 0.4)}}>
			<div style={{...cristal, display: 'flex', alignItems: 'center', gap: 14, fontFamily: INTER, fontWeight: 700, fontSize: 28, color: '#f5f5f7', padding: '12px 26px', borderRadius: 40}}>
				<span style={{width: 16, height: 16, borderRadius: 8, background: n.color, boxShadow: `0 0 16px ${n.color}`}} />
				Nivel {nivel + 1} · {n.nombre}
			</div>
			<div style={{...cristal, display: 'flex', gap: 10, padding: '16px 22px', borderRadius: 40}}>
				{Array.from({length: total}, (_, k) => {
					const hecha = k < actual || (k === actual && resuelta);
					const es = k === actual;
					return <div key={k} style={{width: es ? 36 : 14, height: 14, borderRadius: 7, background: hecha ? n.color : es ? '#f5f5f7' : 'rgba(255,255,255,0.2)'}} />;
				})}
			</div>
			<div style={{...cristal, fontFamily: INTER, fontWeight: 600, fontSize: 28, color: GRIS, padding: '12px 26px', borderRadius: 40}}>
				<span style={{color: '#f5f5f7', fontWeight: 800}}>{actual + 1}</span>/{total} · {tipo}
			</div>
		</div>
	);
};

// ---------------------------------------------------------------- reloj de 5 s
const Reloj: React.FC<{t: number; x: number; y: number; color: string; T: Tiempos}> = ({t, x, y, color, T}) => {
	const dur = T.rev - T.reloj;
	const p = Math.min(Math.max((t - T.reloj) / dur, 0), 1);
	const vis = rampa(t, T.reloj - 0.3, 0.3) * (1 - rampa(t, T.rev + 0.2, 0.3));
	if (vis <= 0.01) return null;
	const r = 64;
	const c = 2 * Math.PI * r;
	const n = Math.max(1, Math.ceil(dur * (1 - p)));
	const urgente = p > 0.6;
	return (
		<div style={{...cristal, position: 'absolute', left: x - 90, top: y - 90, width: 180, height: 180, borderRadius: 90, opacity: vis}}>
			<svg width={180} height={180} style={{position: 'absolute', left: -1, top: -1}}>
				<circle cx={90} cy={90} r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth={10} />
				<circle cx={90} cy={90} r={r} fill="none" stroke={urgente ? ROJO : color} strokeWidth={10} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * p} transform="rotate(-90 90 90)" />
			</svg>
			<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', ...titular, fontSize: 68, color: urgente ? ROJO : '#f5f5f7', transform: `scale(${p < 1 ? 1 + 0.1 * (1 - ((t - T.reloj) % 1)) : 1})`}}>{p < 1 ? n : '¡Ya!'}</div>
		</div>
	);
};

// ---------------------------------------------------------------- revelación: retrato + nombre + «¿Lo sabías?»
const Revelacion: React.FC<{f: Ficha; t: number; t0: number; color: string; extra?: React.ReactNode}> = ({f, t, t0, color, extra}) => {
	const e = pop(t, t0, 0.5);
	if (e <= 0.001) return null;
	return (
		<div style={{position: 'absolute', left: 140, right: 140, top: 190, bottom: 110, display: 'flex', alignItems: 'center', gap: 70, opacity: Math.min(e * 1.4, 1), transform: `translateY(${(1 - e) * 30}px)`}}>
			<div style={{width: 500, height: 660, flexShrink: 0, borderRadius: 36, overflow: 'hidden', boxShadow: `0 40px 100px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.15)`}}>
				<Img src={staticFile(f.foto)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${f.foco[0] * 100}% ${f.foco[1] * 100}%`, transform: `scale(${1.05 + 0.05 * rampa(t, t0, 3)})`}} />
			</div>
			<div style={{flex: 1}}>
				<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 30, letterSpacing: 2, color, opacity: rampa(t, t0 + 0.2, 0.4)}}>La respuesta</div>
				<div style={{...titular, ...degradado(), fontSize: 92, lineHeight: 1.02, marginTop: 6}}>{f.autor}</div>
				<div style={{...cristal, borderRadius: 28, padding: '30px 36px', marginTop: 34, opacity: rampa(t, t0 + 0.5, 0.4), transform: `translateY(${(1 - rampa(t, t0 + 0.5, 0.4)) * 20}px)`}}>
					<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 26, letterSpacing: 2, color: GRIS}}>¿LO SABÍAS?</div>
					<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 44, lineHeight: 1.3, color: '#f5f5f7', marginTop: 8}}>{f.dato}</div>
				</div>
				<div style={{marginTop: 26, opacity: rampa(t, t0 + 1.0, 0.5)}}>{extra}</div>
			</div>
		</div>
	);
};

/** Botón de respuesta (cristal) que se pone verde o rojo al revelar. */
const Boton: React.FC<{letra?: string; texto: string; t: number; t0: number; rev: number; ok: boolean; ancho: number; tam?: number}> = ({letra, texto, t, t0, rev, ok, ancho, tam = 50}) => {
	const e = pop(t, t0, 0.45);
	const m = rampa(t, rev, 0.3);
	return (
		<div
			style={{
				...cristal,
				...(m > 0 ? {background: ok ? 'rgba(52,199,89,0.85)' : 'rgba(255,255,255,0.04)', border: `1px solid ${ok ? VERDE : 'rgba(255,255,255,0.08)'}`} : {}),
				width: ancho,
				height: 116,
				display: 'flex',
				alignItems: 'center',
				gap: 22,
				padding: '0 30px',
				borderRadius: 58,
				opacity: Math.min(e * 1.4, 1) * (m > 0 && !ok ? 0.45 : 1),
				transform: `translateY(${(1 - e) * 50}px) scale(${m > 0 && ok ? 1 + 0.05 * Math.sin(Math.PI * Math.min(m, 1)) : 1})`,
				boxShadow: m > 0 && ok ? `0 0 60px rgba(52,199,89,0.6)` : cristal.boxShadow,
			}}
		>
			{letra && <div style={{width: 72, height: 72, borderRadius: 36, flexShrink: 0, background: '#f5f5f7', color: '#000', fontFamily: INTER, fontWeight: 800, fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{letra}</div>}
			<div style={{fontFamily: INTER, fontWeight: 700, fontSize: tam, color: '#f5f5f7', flex: 1, textAlign: letra ? 'left' : 'center'}}>{texto}</div>
			{m > 0 && <div style={{fontFamily: INTER, fontWeight: 800, fontSize: 54, color: '#fff', transform: `scale(${pop(t, rev, 0.35)})`}}>{ok ? '✓' : '✕'}</div>}
		</div>
	);
};

const tiemposCita = (texto: string, t0: number, t1: number) => {
	const n = texto.split(' ').length;
	return Array.from({length: n}, (_, i) => t0 + ((t1 - t0) * i) / n);
};

const Bandera: React.FC<{src?: string; alto: number}> = ({src, alto}) =>
	src ? <Img src={staticFile(src)} style={{height: alto, width: (alto * 4) / 3, borderRadius: alto * 0.12, boxShadow: '0 8px 24px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.2)', objectFit: 'cover'}} /> : null;

// ---------------------------------------------------------------- tipos de pregunta
const Planteamiento: React.FC<{p: Pregunta; t: number; color: string}> = ({p, t, color}) => {
	const T = tiemposDe(p);
	const fuera = rampa(t, T.dato - 0.4, 0.4);
	const st: React.CSSProperties = {position: 'absolute', inset: 0, opacity: 1 - fuera};
	const titulo = (txt: React.ReactNode, top = 170) => (
		<div style={{position: 'absolute', top, left: 140, right: 140, textAlign: 'center', ...titular, fontSize: 64, opacity: rampa(t, T.pregunta, 0.4), transform: `translateY(${(1 - rampa(t, T.pregunta, 0.4)) * 16}px)`}}>{txt}</div>
	);
	if (p.tipo === 'quien') {
		// frases largas: letra más pequeña y tarjetas algo más abajo y más pequeñas
		const largo = p.cita.length > 42;
		return (
			<div style={st}>
				<div style={{position: 'absolute', top: largo ? 140 : 165, left: 160, right: 160, display: 'flex', justifyContent: 'center'}}>
					<CitaPluma cita={p.cita} tiempos={tiemposCita(p.cita, T.cita?.[0] ?? T.pregunta, T.cita?.[1] ?? T.opciones)} finVoz={T.cita?.[1] ?? T.opciones} t={t} tam={largo ? 60 : 84} ancho={1600} apagar={0} />
				</div>
				<div style={{position: 'absolute', inset: 0, transform: `scale(${largo ? 1.25 : 1.45})`, transformOrigin: `${W / 2}px ${largo ? 250 : 330}px`}}>
					<Opciones opciones={p.opciones} correcta={p.correcta} entradas={[0, 1, 2].map((k) => T.opciones + k * 0.4)} t={t} rev={T.rev} salida={0} cx={W / 2} top={330} />
				</div>
			</div>
		);
	}
	if (p.tipo === 'completa') {
		const lleno = rampa(t, T.rev + 0.3, 0.4);
		return (
			<div style={st}>
				<div style={{position: 'absolute', top: p.antes.length > 34 ? 190 : 260, left: 120, right: 120, textAlign: 'center', fontFamily: 'Playfair Display', fontStyle: 'italic', fontWeight: 700, fontSize: p.antes.length > 34 ? 72 : 84, lineHeight: 1.2, color: '#f5f5f7', textWrap: 'balance', opacity: rampa(t, T.pregunta, 0.5)} as React.CSSProperties}>
					«{p.antes}{' '}
					<span style={{display: 'inline-block', minWidth: 300, borderBottom: `8px solid ${lleno > 0 ? VERDE : color}`, color: VERDE, transform: `scale(${1 + 0.15 * Math.sin(Math.PI * lleno)})`}}>
						<span style={{opacity: lleno}}>{p.opciones[p.correcta]}</span>
					</span>
					.»
				</div>
				<div style={{position: 'absolute', top: 600, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 40}}>
					{p.opciones.map((o, k) => (
						<Boton key={k} letra={'ABC'[k]} texto={o} t={t} t0={T.opciones + k * 0.35} rev={T.rev} ok={k === p.correcta} ancho={470} />
					))}
				</div>
			</div>
		);
	}
	if (p.tipo === 'vf') {
		const sello = pop(t, T.rev + 0.15, 0.4);
		return (
			<div style={st}>
				<div style={{position: 'absolute', top: 170, left: 160, right: 760, display: 'flex', alignItems: 'center', height: 420}}>
					<CitaPluma cita={p.cita} tiempos={tiemposCita(p.cita, T.cita?.[0] ?? T.pregunta, T.cita?.[1] ?? T.opciones - 0.4)} finVoz={T.cita?.[1] ?? T.opciones} t={t} tam={78} ancho={1000} apagar={0} />
				</div>
				<div style={{position: 'absolute', top: 160, right: 180, width: 420, textAlign: 'center', opacity: rampa(t, T.opciones - 0.4, 0.4)}}>
					<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 36, color: GRIS, marginBottom: 14}}>¿Es de…?</div>
					<div style={{position: 'relative', width: 420, height: 400, borderRadius: 36, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.15)'}}>
						<Img src={staticFile(p.propuesto.foto)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${p.propuesto.foco[0] * 100}% ${p.propuesto.foco[1] * 100}%`, transform: `scale(${p.propuesto.zoom ?? 1})`, transformOrigin: `${p.propuesto.foco[0] * 100}% ${p.propuesto.foco[1] * 100}%`, filter: `grayscale(${p.verdadero ? 0 : sello})`}} />
						{sello > 0 && (
							<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: `rgba(0,0,0,${0.35 * sello})`}}>
								<div style={{width: 170, height: 170, borderRadius: 85, background: p.verdadero ? VERDE : ROJO, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: INTER, fontWeight: 800, fontSize: 96, color: '#fff', transform: `scale(${sello})`, boxShadow: '0 10px 40px rgba(0,0,0,0.5)'}}>{p.verdadero ? '✓' : '✕'}</div>
							</div>
						)}
					</div>
					<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 40, color: '#f5f5f7', marginTop: 14}}>{p.propuesto.nombre}</div>
				</div>
				<div style={{position: 'absolute', top: 780, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 50}}>
					<Boton texto="Verdadero" t={t} t0={T.opciones} rev={T.rev} ok={p.verdadero} ancho={520} tam={52} />
					<Boton texto="Falso" t={t} t0={T.opciones + 0.35} rev={T.rev} ok={!p.verdadero} ancho={520} tam={52} />
				</div>
			</div>
		);
	}
	if (p.tipo === 'pais') {
		const m = rampa(t, T.rev, 0.3);
		return (
			<div style={st}>
				{titulo(<>¿De qué país era <span style={{color}}>{p.ficha.autor}</span>?</>)}
				<div style={{position: 'absolute', top: 300, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 46}}>
					{p.paises.map((pa, k) => {
						const e = pop(t, T.opciones + k * 0.4, 0.45);
						const ok = k === p.correcta;
						return (
							<div key={k} style={{...cristal, ...(m > 0 && ok ? {border: `2px solid ${VERDE}`, boxShadow: '0 0 70px rgba(52,199,89,0.5)'} : {}), width: 500, padding: 26, borderRadius: 40, textAlign: 'center', opacity: Math.min(e * 1.4, 1) * (m > 0 && !ok ? 0.4 : 1), transform: `translateY(${(1 - e) * 60}px) scale(${m > 0 && ok ? 1.05 : 1})`}}>
								<div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18}}>
									<div style={{width: 64, height: 64, borderRadius: 32, background: '#f5f5f7', color: '#000', fontFamily: INTER, fontWeight: 800, fontSize: 36, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{'ABC'[k]}</div>
									<Bandera src={pa.bandera} alto={84} />
								</div>
								<MapaPais pais={pa} t={t} t0={T.opciones + k * 0.4} color={m > 0 && ok ? VERDE : '#8e8e93'} ancho={448} alto={300} />
								<div style={{fontFamily: INTER, fontWeight: 800, fontSize: 50, color: m > 0 && ok ? VERDE : '#f5f5f7', marginTop: 16}}>{pa.nombre}</div>
							</div>
						);
					})}
				</div>
			</div>
		);
	}
	if (p.tipo === 'siglo') {
		const x0 = 640;
		const x1 = 1760;
		// eje: de medio siglo antes de la primera opción a medio siglo después de la última
		const a0 = Math.min(...p.opciones.map((o) => o.desde), p.vida.nace) - 50;
		const a1 = Math.max(...p.opciones.map((o) => o.hasta), p.vida.muere) + 50;
		const marcas = Array.from({length: 40}, (_, k) => Math.ceil(a0 / 100) * 100 + k * 100).filter((a) => a <= a1);
		const x = (a: number) => x0 + ((a - a0) / (a1 - a0)) * (x1 - x0);
		const crece = rampa(t, T.pregunta + 0.4, 1.2);
		const m = rampa(t, T.rev, 0.3);
		return (
			<div style={st}>
				{/* el retrato de quien hablamos, junto a la pregunta */}
				<div style={{position: 'absolute', left: 140, top: 190, width: 400, height: 520, borderRadius: 36, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.15)', opacity: rampa(t, T.pregunta, 0.4), transform: `scale(${0.95 + 0.05 * rampa(t, T.pregunta, 0.6)})`}}>
					<Img src={staticFile(p.ficha.foto)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${p.ficha.foco[0] * 100}% ${p.ficha.foco[1] * 100}%`}} />
				</div>
				<div style={{position: 'absolute', left: 640, right: 140, top: 210, ...titular, fontSize: 60, lineHeight: 1.1, opacity: rampa(t, T.pregunta, 0.4)}}>
					¿En qué siglo vivió <span style={{color}}>{p.ficha.autor}</span>?
				</div>
				<svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
					<line x1={x0} y1={640} x2={lerp(x0, x1, crece)} y2={640} stroke="rgba(255,255,255,0.5)" strokeWidth={4} strokeLinecap="round" />
					{marcas.map((a) => (
						<g key={a} opacity={crece}>
							<line x1={x(a)} y1={626} x2={x(a)} y2={654} stroke="rgba(255,255,255,0.45)" strokeWidth={3} />
							<text x={x(a)} y={700} fill={GRIS} fontFamily={INTER} fontWeight={600} fontSize={28} textAnchor="middle">{a}</text>
						</g>
					))}
					{p.opciones.map((o, k) => {
						const e = pop(t, T.opciones + k * 0.4, 0.45);
						const ok = k === p.correcta;
						const col = m > 0 ? (ok ? VERDE : 'rgba(255,255,255,0.08)') : 'rgba(255,255,255,0.12)';
						return (
							<g key={k} opacity={Math.min(e * 1.4, 1)}>
								<rect x={x(o.desde) + 6} y={490} width={(x(o.hasta) - x(o.desde) - 12) * Math.min(e, 1)} height={110} rx={55} fill={col} stroke={m > 0 && ok ? VERDE : 'rgba(255,255,255,0.25)'} strokeWidth={1.5} />
								<text x={(x(o.desde) + x(o.hasta)) / 2} y={536} fill={GRIS} fontFamily={INTER} fontWeight={800} fontSize={30} textAnchor="middle">{'ABC'[k]}</text>
								<text x={(x(o.desde) + x(o.hasta)) / 2} y={582} fill="#f5f5f7" fontFamily={INTER} fontWeight={800} fontSize={Math.min(44, ...p.opciones.map((q) => (x(q.hasta) - x(q.desde) - 34) / (q.rotulo.length * 0.62)))} textAnchor="middle">{o.rotulo}</text>
							</g>
						);
					})}
				</svg>
				{m > 0 && (
					<div style={{position: 'absolute', left: x(p.vida.nace) - 20, top: 740, opacity: rampa(t, T.rev + 0.3, 0.3)}}>
						<LineaVida nace={p.vida.nace} muere={p.vida.muere} t={t} t0={T.rev + 0.3} color={VERDE} ancho={x(p.vida.muere) - x(p.vida.nace) + 40} />
					</div>
				)}
			</div>
		);
	}
	// pistas: la silueta se va descubriendo
	const desvela = rampa(t, T.rev, 0.9);
	const an = 520;
	const al = an * p.proporcion;
	return (
		<div style={st}>
			<div style={{position: 'absolute', left: 180, top: 180, width: an, height: Math.min(al, 760), overflow: 'hidden', borderRadius: 36, boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 0 ${desvela > 0.5 ? 3 : 1}px ${desvela > 0.5 ? VERDE : 'rgba(255,255,255,0.18)'}`, opacity: rampa(t, T.pregunta, 0.4)}}>
				{p.recorte ? (
					<>
						<Img src={staticFile(p.ficha.foto)} style={{position: 'absolute', left: 0, top: 0, width: an, height: al, objectFit: 'cover', filter: `brightness(${lerp(0.6, 1, desvela)})`}} />
						<Img src={staticFile(p.recorte)} style={{position: 'absolute', left: 0, top: 0, width: an, height: al, objectFit: 'cover', filter: 'brightness(0)', opacity: 1 - desvela}} />
					</>
				) : (
					// sin recorte: el retrato muy desenfocado y oscuro, que se aclara al revelar
					<Img src={staticFile(p.ficha.foto)} style={{position: 'absolute', left: 0, top: 0, width: an, height: al, objectFit: 'cover', objectPosition: `${p.ficha.foco[0] * 100}% ${p.ficha.foco[1] * 100}%`, filter: `blur(${lerp(38, 0, desvela)}px) brightness(${lerp(0.35, 1, desvela)})`, transform: `scale(${lerp(1.25, 1, desvela)})`}} />
				)}
				<div style={{position: 'absolute', left: 0, right: 0, top: '22%', textAlign: 'center', ...titular, fontSize: 240, color, opacity: 1 - desvela, textShadow: `0 0 40px ${color}`}}>?</div>
			</div>
			<div style={{position: 'absolute', left: 800, right: 160, top: 200}}>
				<div style={{...titular, fontSize: 56, marginBottom: 34, opacity: rampa(t, T.pregunta, 0.4)}}>¿Quién es? Tres pistas</div>
				{p.pistas.map((pi, k) => {
					const e = pop(t, T.pistas?.[k] ?? T.pregunta + 0.6 + k * 1.0, 0.45);
					return (
						<div key={k} style={{...cristal, display: 'flex', alignItems: 'center', gap: 26, marginBottom: 24, padding: '22px 32px', borderRadius: 32, opacity: Math.min(e * 1.4, 1), transform: `translateX(${(1 - e) * 80}px)`}}>
							<div style={{fontSize: 56}}>{pi.icono}</div>
							<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 50, color: '#f5f5f7'}}>{pi.texto}</div>
						</div>
					);
				})}
				{desvela > 0 && <div style={{...titular, fontSize: 68, color: VERDE, marginTop: 10, transform: `scale(${pop(t, T.rev + 0.2, 0.4)})`}}>{p.ficha.autor} ✓</div>}
			</div>
		</div>
	);
};

const BloquePregunta: React.FC<{p: Pregunta; i: number; total: number}> = ({p, i, total}) => {
	const t = useCurrentFrame() / FPS;
	const T = tiemposDe(p);
	const color = NIVELES[p.nivel].color;
	const tinta = Math.max(1 - rampa(t, 0, 0.5), rampa(t, T.fin - 0.5, 0.5));
	const extra =
		p.tipo === 'pais' ? (
			<div style={{display: 'flex', alignItems: 'center', gap: 20}}>
				<Bandera src={p.paises[p.correcta].bandera} alto={64} />
				<div style={{fontFamily: INTER, fontWeight: 700, fontSize: 40, color: '#f5f5f7'}}>
					{p.paises[p.correcta].nombre} · <span style={{color: GRIS}}>{p.paises[p.correcta].ciudad}</span>
				</div>
			</div>
		) : null;
	return (
		<AbsoluteFill>
			<Cabecera nivel={p.nivel} actual={i} total={total} tipo={ROTULO_TIPO[p.tipo]} t={t} resuelta={t > T.rev} />
			<Planteamiento p={p} t={t} color={color} />
			<Reloj t={t} x={W - 150} y={H - 150} color={color} T={T} />
			<Revelacion f={p.ficha} t={t} t0={T.dato} color={color} extra={extra} />
			{/* transición: fundido a negro con un leve zoom */}
			{tinta > 0.001 && <AbsoluteFill style={{background: '#000', opacity: tinta}} />}
			{[0, 1, 2, 3, 4].map((k) => (
				<Sequence key={k} from={Math.round((T.reloj + k) * FPS)} durationInFrames={20}>
					<Audio src={staticFile('sfx/pop.wav')} volume={0.12 + k * 0.04} />
				</Sequence>
			))}
			<Sequence from={Math.round(T.rev * FPS)} durationInFrames={45}>
				<Audio src={staticFile('sfx/campana.wav')} volume={0.45} />
			</Sequence>
			<Sequence from={Math.round((T.fin - 0.5) * FPS)} durationInFrames={30}>
				<Audio src={staticFile('sfx/whoosh.wav')} volume={0.3} />
			</Sequence>
			{/* narración: el planteamiento al empezar y la respuesta al revelar */}
			{p.voz && (
				<>
					<Sequence from={Math.round((T.vozA ?? T.pregunta) * FPS)}>
						<Audio src={staticFile(p.voz.a)} />
					</Sequence>
					<Sequence from={Math.round((T.vozB ?? T.rev) * FPS)}>
						<Audio src={staticFile(p.voz.b)} />
					</Sequence>
				</>
			)}
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- intro, cortinilla de nivel y final
const Intro: React.FC<{d: DatosQuizLargo; dur: number}> = ({d, dur}) => {
	const t = useCurrentFrame() / FPS;
	const sale = rampa(t, dur - 0.6, 0.6);
	return (
		<AbsoluteFill style={{opacity: 1 - sale, transform: `scale(${1 + 0.03 * sale})`}}>
			<div style={{position: 'absolute', top: 140, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
				<Comillas tipo="abre" t={t} t0={0.1} tam={300} />
			</div>
			<div style={{position: 'absolute', top: 300, left: 0, right: 0, textAlign: 'center', ...titular, ...degradado(), fontSize: 168, letterSpacing: -5, opacity: rampa(t, 0.5, 0.6), transform: `translateY(${(1 - rampa(t, 0.5, 0.8)) * 30}px)`}}>{d.titulo}</div>
			<div style={{position: 'absolute', top: 520, left: 0, right: 0, textAlign: 'center', fontFamily: INTER, fontWeight: 600, fontSize: 50, color: GRIS, opacity: rampa(t, 1.1, 0.5)}}>{d.subtitulo}</div>
			<div style={{position: 'absolute', top: 680, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 28}}>
				{[`${d.total} frases`, `${NIVELES.length} niveles`, 'Cuenta tus aciertos'].map((x, k) => {
					const e = pop(t, 1.8 + k * 0.3, 0.45);
					return (
						<div key={k} style={{...cristal, fontFamily: INTER, fontWeight: 700, fontSize: 42, color: '#f5f5f7', padding: '20px 38px', borderRadius: 48, opacity: Math.min(e * 1.4, 1), transform: `translateY(${(1 - e) * 40}px)`}}>{x}</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', top: 870, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 36, opacity: rampa(t, 3, 0.5)}}>
				{NIVELES.map((n) => (
					<div key={n.nombre} style={{display: 'flex', alignItems: 'center', gap: 12, fontFamily: INTER, fontWeight: 600, fontSize: 32, color: GRIS}}>
						<span style={{width: 14, height: 14, borderRadius: 7, background: n.color, boxShadow: `0 0 14px ${n.color}`}} />
						{n.nombre}
					</div>
				))}
			</div>
		</AbsoluteFill>
	);
};

const Cortinilla: React.FC<{nivel: number; dur: number}> = ({nivel, dur}) => {
	const t = useCurrentFrame() / FPS;
	const n = NIVELES[nivel];
	const e = rampa(t, 0.15, 0.6);
	const sale = rampa(t, dur - 0.5, 0.5);
	return (
		<AbsoluteFill style={{opacity: 1 - sale}}>
			<AbsoluteFill style={{background: '#000', opacity: Math.min(t / 0.3, 1)}} />
			<div style={{position: 'absolute', left: W / 2 - 600, top: H / 2 - 600, width: 1200, height: 1200, borderRadius: '50%', background: n.color, opacity: 0.45 * e, filter: 'blur(180px)', transform: `scale(${0.6 + 0.4 * e})`}} />
			<div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
				<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 44, color: GRIS, letterSpacing: 2, opacity: e}}>Nivel {nivel + 1}</div>
				<div style={{...titular, ...degradado('#ffffff', n.color), fontSize: 260, letterSpacing: -8, lineHeight: 1.1, opacity: e, transform: `scale(${1.15 - 0.15 * e})`, filter: `blur(${(1 - e) * 12}px)`}}>{n.nombre}</div>
			</div>
		</AbsoluteFill>
	);
};

const Final: React.FC<{total: number; dur: number}> = ({total, dur: FINAL}) => {
	const t = useCurrentFrame() / FPS;
	const escala = [
		{r: `0–${Math.round(total / 4)}`, t: 'Aprendiz'},
		{r: `${Math.round(total / 4) + 1}–${Math.round(total / 2)}`, t: 'Lector curioso'},
		{r: `${Math.round(total / 2) + 1}–${total - 3}`, t: 'Erudito'},
		{r: `${total - 2}–${total}`, t: 'Sabio'},
	];
	return (
		<AbsoluteFill>
			<div style={{position: 'absolute', top: 100, left: 0, right: 0, textAlign: 'center', ...titular, ...degradado(), fontSize: 130, letterSpacing: -4, opacity: rampa(t, 0.2, 0.5)}}>¿Cuántas acertaste?</div>
			<div style={{position: 'absolute', top: 310, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 28}}>
				{escala.map((x, k) => {
					const e = pop(t, 0.8 + k * 0.25, 0.45);
					return (
						<div key={k} style={{...cristal, width: 360, padding: '30px 20px', borderRadius: 36, textAlign: 'center', opacity: Math.min(e * 1.4, 1), transform: `translateY(${(1 - e) * 50}px)`}}>
							<div style={{...titular, fontSize: 70, color: NIVELES[k].color}}>{x.r}</div>
							<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 36, color: '#f5f5f7', marginTop: 4}}>{x.t}</div>
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', top: 560, left: 0, right: 0, textAlign: 'center', fontFamily: INTER, fontWeight: 600, fontSize: 44, color: GRIS, opacity: rampa(t, 2.0, 0.5)}}>Escribe tu resultado en los comentarios</div>
			<Suscribete t={t} s0={3.0} fin={FINAL - 0.8} cx={W / 2} top={650} titulo={false} />
			{t > FINAL - 1.6 && (
				<div style={{position: 'absolute', top: 850, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: 1 - rampa(t, FINAL - 0.5, 0.4)}}>
					<Comillas tipo="cierra" t={t} t0={FINAL - 1.6} tam={220} />
				</div>
			)}
		</AbsoluteFill>
	);
};

/** Música de un tramo, con fundido de entrada y de salida para encadenar con el siguiente. */
const Pista: React.FC<{src: string; dur: number; vol: number}> = ({src, dur, vol}) => {
	const f = Math.round(dur * FPS);
	return <Audio src={staticFile(src)} volume={(fr) => vol * interpolate(fr, [0, 15, f - 20, f], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />;
};

export const QuizLargo: React.FC<DatosQuizLargo> = (d) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const {pasos, tramos} = plan(d);
	const actual = pasos.find((p) => t >= p.desde && t < p.desde + p.dur);
	const nivelActual = actual && (actual.tipo === 'pregunta' || actual.tipo === 'nivel') ? d.preguntas[actual.i ?? 0].nivel : -1;
	const final = pasos[pasos.length - 1];
	const intro = pasos[0];
	// con narración, la música baja para que la voz se entienda bien
	const vol = d.voces ? 0.09 : 0.16;
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<Fondo t={t} color={nivelActual >= 0 ? NIVELES[nivelActual].color : '#BF5AF2'} />
			{pasos.map((p, k) => (
				<Sequence key={k} from={Math.round(p.desde * FPS)} durationInFrames={Math.round(p.dur * FPS)}>
					{p.tipo === 'intro' && <Intro d={d} dur={p.dur} />}
					{p.tipo === 'nivel' && <Cortinilla nivel={d.preguntas[p.i ?? 0].nivel} dur={p.dur} />}
					{p.tipo === 'pregunta' && <BloquePregunta p={d.preguntas[p.i ?? 0]} i={p.i ?? 0} total={d.total} />}
					{p.tipo === 'final' && <Final total={d.total} dur={p.dur} />}
					{p.tipo === 'nivel' && <Audio src={staticFile('sfx/subida.wav')} volume={0.3} />}
					{/* narración de la intro, de cada nivel y del final */}
					{d.voces && p.tipo === 'intro' && (
						<Sequence from={Math.round(0.5 * FPS)}>
							<Audio src={staticFile(d.voces.intro)} />
						</Sequence>
					)}
					{d.voces && p.tipo === 'nivel' && d.voces.niveles[d.preguntas[p.i ?? 0].nivel] && (
						<Sequence from={Math.round(0.3 * FPS)}>
							<Audio src={staticFile(d.voces.niveles[d.preguntas[p.i ?? 0].nivel])} />
						</Sequence>
					)}
					{d.voces && p.tipo === 'final' && (
						<Sequence from={Math.round(0.4 * FPS)}>
							<Audio src={staticFile(d.voces.final)} />
						</Sequence>
					)}
				</Sequence>
			))}
			{/* música variada: una pista por tramo */}
			<Sequence from={0} durationInFrames={Math.round(intro.dur * FPS)}>
				<Pista src={d.musica.intro} dur={intro.dur} vol={vol} />
			</Sequence>
			{tramos.map((tr, k) => (
				<Sequence key={`m${k}`} from={Math.round(tr.desde * FPS)} durationInFrames={Math.round((tr.hasta - tr.desde) * FPS)}>
					<Pista src={d.musica.niveles[tr.nivel] ?? d.musica.niveles[0]} dur={tr.hasta - tr.desde} vol={vol} />
				</Sequence>
			))}
			<Sequence from={Math.round(final.desde * FPS)} durationInFrames={Math.round(final.dur * FPS)}>
				<Pista src={d.musica.final} dur={final.dur} vol={vol} />
			</Sequence>
		</AbsoluteFill>
	);
};
