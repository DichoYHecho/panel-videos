/**
 * Formato «El origen» (prototipo v1, fase 2, 27 nov 2026). De dónde viene una expresión. Mismo estilo minimalista
 * por escenas que los otros formatos, con piezas propias de esta historia (regla de variedad):
 * 1) gancho; 2) mapa con alfiler y la estela dibujada; 3) la ley en pictogramas; 4) barras daño/castigo con el
 * límite; 5) línea de tiempo horizontal con cámara que sigue la narración; 6) pregunta con dos opciones (1 / 2).
 * Sin fuentes en pantalla (van en la descripción).
 */
import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {AMARILLO, FPS, INTER, ROJO, lerp, pop, rampa, suave} from './base';
import {MapaPais, type Pais} from './piezas';
import {Entra, Palabras, type Palabra} from './LoDijo';

type Hito = {titulo: string; sub: string; icono: 'estela' | 'libro' | 'mejilla'; frase?: string; t: number};
export type DatosOrigen = {
	expresion: string;
	voz: {archivo: string; dur: number; palabras: Palabra[]};
	musica: string;
	gancho: {a: string; b: string; tB: number};
	pais: Pais;
	t: {mapa: number; anios: number; estela: number; lugar: number; ley: number; ley2: number; idea: number; linea: number; pregunta: number};
	hace: string; // «hace casi 4.000 años»
	ley: {rotulo: string; a: string; b: string};
	hitos: Hito[];
	pregunta: string;
	opciones: [string, string];
};

const ANCHO = 1080;
const ALTO = 1920;
const COLA = 0.6;
const FONDO = '#0a0a0a';

export const duracionOrigen = (d: DatosOrigen) => Math.round((d.voz.dur + COLA) * FPS);

// ---------------------------------------------------------------- pictogramas
const Estela: React.FC<{alto: number; e: number}> = ({alto, e}) => {
	const lineas = 16;
	return (
		<svg width={alto * 0.48} height={alto} viewBox="0 0 240 500">
			<path d="M30 500 L30 120 Q30 20 120 20 Q210 20 210 120 L210 500 Z" fill="#1c1c1c" stroke="rgba(255,255,255,0.55)" strokeWidth={4} />
			<path d="M55 140 Q55 60 120 60 Q185 60 185 140 Z" fill="none" stroke={AMARILLO} strokeWidth={3} opacity={0.8} />
			{Array.from({length: lineas}, (_, i) => {
				const y = 170 + i * 19;
				const k = rampa(e * lineas, i, 1);
				return <line key={i} x1={55} y1={y} x2={lerp(55, 185 - (i % 3) * 14, k)} y2={y} stroke="rgba(255,255,255,0.55)" strokeWidth={5} strokeDasharray="6 5" />;
			})}
		</svg>
	);
};

const Ojo: React.FC<{tam: number; tachado: number; color: string}> = ({tam, tachado, color}) => (
	<svg width={tam} height={tam * 0.6} viewBox="0 0 200 120">
		<path d="M10 60 Q100 -20 190 60 Q100 140 10 60 Z" fill="none" stroke="#fff" strokeWidth={9} />
		<circle cx={100} cy={60} r={26} fill="#fff" />
		<circle cx={100} cy={60} r={11} fill={FONDO} />
		<line x1={30} y1={110} x2={lerp(30, 170, tachado)} y2={lerp(110, 10, tachado)} stroke={color} strokeWidth={14} strokeLinecap="round" />
	</svg>
);

const Icono: React.FC<{tipo: Hito['icono']; tam: number}> = ({tipo, tam}) => {
	if (tipo === 'estela') return <Estela alto={tam} e={1} />;
	if (tipo === 'libro')
		return (
			<svg width={tam} height={tam} viewBox="0 0 100 100">
				<path d="M10 22 Q30 14 50 24 Q70 14 90 22 L90 84 Q70 76 50 86 Q30 76 10 84 Z" fill="none" stroke="#fff" strokeWidth={5} strokeLinejoin="round" />
				<line x1={50} y1={24} x2={50} y2={86} stroke="#fff" strokeWidth={5} />
				<line x1={40} y1={44} x2={40} y2={60} stroke={AMARILLO} strokeWidth={5} />
				<line x1={32} y1={52} x2={48} y2={52} stroke={AMARILLO} strokeWidth={5} />
			</svg>
		);
	// mano abierta: no devolver el golpe
	return (
		<svg width={tam} height={tam} viewBox="0 0 100 100">
			<g fill="none" stroke="#fff" strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round">
				<path d="M30 56 L30 26 Q30 20 35.5 20 Q41 20 41 26 L41 50" />
				<path d="M41 48 L41 16 Q41 10 46.5 10 Q52 10 52 16 L52 48" />
				<path d="M52 48 L52 20 Q52 14 57.5 14 Q63 14 63 20 L63 50" />
				<path d="M63 50 L63 30 Q63 24 68.5 24 Q74 24 74 30 L74 64 Q74 90 50 90 Q34 90 26 76 L14 56 Q11 50 16 47 Q21 44 25 49 L30 56" />
			</g>
			<circle cx={52} cy={66} r={6} fill={AMARILLO} />
		</svg>
	);
};

// ---------------------------------------------------------------- escenas
const EscenaGancho: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const punch = t > d.gancho.tB - 0.05 ? 1 + 0.06 * (1 - suave((t - d.gancho.tB + 0.05) / 0.35)) : 1;
	const eExp = pop(t, 0.8, 0.45);
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{position: 'absolute', width: 900, height: 900, borderRadius: '50%', background: 'radial-gradient(circle, rgba(245,197,24,0.10), transparent 65%)', transform: `scale(${1 + 0.15 * Math.sin(t * 1.3)})`}} />
			<div style={{width: 920, textAlign: 'center', fontFamily: INTER, letterSpacing: -2, lineHeight: 1.1, transform: `scale(${(1 + 0.04 * (t / d.t.mapa)) * punch})`}}>
				<div style={{fontSize: 64, fontWeight: 700, color: 'rgba(255,255,255,0.75)', opacity: rampa(t, 0, 0.3)}}>¿Sabías que</div>
				<div style={{fontSize: 150, fontWeight: 900, color: AMARILLO, margin: '10px 0 24px', opacity: Math.min(eExp * 1.5, 1), transform: `scale(${0.7 + 0.3 * eExp})`}}>«{d.expresion}»</div>
				<div style={{fontSize: 74, fontWeight: 800, color: '#fff'}}>
					<Palabras txt={d.gancho.a} t={t} t0={1.8} paso={0.18} tam={74} />
				</div>
				<div style={{fontSize: 96, fontWeight: 900, marginTop: 20}}>
					<Palabras txt={d.gancho.b} t={t} t0={d.gancho.tB} paso={0.2} tam={96} color={AMARILLO} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

const EscenaMapa: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const T = d.t;
	const zoom = lerp(1.0, 1.08, suave((t - T.mapa) / (T.ley - T.mapa)));
	const eAnios = pop(t, T.anios - 0.05, 0.4);
	const eEst = suave((t - T.estela + 0.1) / 0.7);
	const eLugar = pop(t, T.lugar - 0.05, 0.4);
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<div style={{position: 'absolute', top: 200, left: 0, width: ANCHO, textAlign: 'center', opacity: Math.min(eAnios * 1.5, 1), transform: `translateY(${40 * (1 - eAnios)}px)`}}>
				<span style={{fontFamily: INTER, fontWeight: 900, fontSize: 86, color: AMARILLO, letterSpacing: -2}}>{d.hace}</span>
			</div>
			<div style={{position: 'absolute', top: 400, left: 90, transform: `scale(${zoom})`, transformOrigin: '50% 50%'}}>
				<MapaPais pais={d.pais} t={t} t0={T.mapa} color="#8a6d12" ancho={900} alto={720} />
			</div>
			<div style={{position: 'absolute', top: 1160, left: 90, opacity: Math.min(eLugar * 1.5, 1), transform: `scale(${0.7 + 0.3 * eLugar})`, transformOrigin: 'left center'}}>
				<span style={{fontFamily: INTER, fontWeight: 900, fontSize: 64, color: '#fff'}}>{d.pais.ciudad}</span>
				<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 32, color: 'rgba(255,255,255,0.6)'}}>{d.pais.nombre}</div>
			</div>
			{/* la estela sube desde abajo */}
			<div style={{position: 'absolute', right: 90, top: lerp(1900, 1080, eEst), textAlign: 'center'}}>
				<Estela alto={440} e={rampa(t, T.estela + 0.3, 1.2)} />
				<div style={{marginTop: 10, fontFamily: INTER, fontWeight: 800, fontSize: 34, color: '#fff', width: 300, marginLeft: -40}}>Código de Hammurabi</div>
			</div>
		</AbsoluteFill>
	);
};

const EscenaLey: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const T = d.t;
	const e1 = pop(t, T.ley - 0.05, 0.4);
	const e2 = pop(t, T.ley2 - 0.05, 0.4);
	const flecha = rampa(t, T.ley2 - 0.4, 0.4);
	const bloque = (e: number, tach: number, txt: string, color: string) => (
		<div style={{textAlign: 'center', opacity: Math.min(e * 1.5, 1), transform: `scale(${0.7 + 0.3 * e})`}}>
			<Ojo tam={340} tachado={tach} color={color} />
			<div style={{marginTop: 18, fontFamily: INTER, fontWeight: 800, fontSize: 46, color: '#fff'}}>{txt}</div>
		</div>
	);
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{position: 'absolute', top: 300, width: ANCHO, textAlign: 'center', opacity: rampa(t, T.ley, 0.4)}}>
				<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 32, letterSpacing: 4, color: '#111', background: '#fff', padding: '10px 24px', borderRadius: 10, textTransform: 'uppercase'}}>{d.ley.rotulo}</span>
			</div>
			<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30, marginTop: 60}}>
				{bloque(e1, rampa(t, T.ley + 0.6, 0.35), d.ley.a, ROJO)}
				<svg width={80} height={110} style={{opacity: flecha}}>
					<line x1={40} y1={0} x2={40} y2={lerp(0, 90, flecha)} stroke={AMARILLO} strokeWidth={8} strokeLinecap="round" />
					<path d="M18 70 L40 100 L62 70" fill="none" stroke={AMARILLO} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" opacity={flecha > 0.9 ? 1 : 0} />
				</svg>
				{bloque(e2, rampa(t, T.ley2 + 0.5, 0.35), d.ley.b, ROJO)}
			</div>
		</AbsoluteFill>
	);
};

/** El castigo crece, choca con la línea del límite (el daño) y se queda ahí. */
const EscenaIdea: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const T = d.t;
	const eDano = rampa(t, T.idea, 0.6);
	const intento = rampa(t, T.idea + 0.6, 0.9);
	const alturaMax = 560;
	const castigo = Math.min(intento * 1.25, 1) * alturaMax; // intenta pasar…
	const tope = Math.min(castigo, alturaMax); // …pero se queda en el límite
	const choque = castigo >= alturaMax ? Math.max(0, 1 - (t - (T.idea + 0.6 + 0.72)) / 0.3) : 0;
	const barra = (h: number, txt: string, color: string, x: number) => (
		<div style={{position: 'absolute', left: x, bottom: 560, width: 230, textAlign: 'center'}}>
			<div style={{height: h, background: color, borderRadius: '18px 18px 0 0'}} />
			<div style={{position: 'absolute', bottom: -70, width: 230, fontFamily: INTER, fontWeight: 800, fontSize: 46, color: '#fff'}}>{txt}</div>
		</div>
	);
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<div style={{position: 'absolute', top: 260, width: ANCHO, textAlign: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 78, color: '#fff', letterSpacing: -2, opacity: rampa(t, T.idea, 0.4)}}>
				ni más, <span style={{color: AMARILLO}}>ni menos</span>
			</div>
			{barra(alturaMax * eDano, 'daño', 'rgba(255,255,255,0.85)', 220)}
			{barra(tope, 'castigo', ROJO, 630)}
			{/* línea del límite */}
			<svg width={ANCHO} height={ALTO} style={{position: 'absolute', inset: 0}}>
				<line x1={160} y1={ALTO - 560 - alturaMax} x2={lerp(160, 920, eDano)} y2={ALTO - 560 - alturaMax} stroke={AMARILLO} strokeWidth={6} strokeDasharray="18 12" />
				<text x={930} y={ALTO - 560 - alturaMax - 20} fill={AMARILLO} fontFamily={INTER} fontWeight={900} fontSize={40} textAnchor="end" opacity={eDano}>LÍMITE</text>
			</svg>
			<AbsoluteFill style={{background: AMARILLO, opacity: choque * 0.18}} />
		</AbsoluteFill>
	);
};

/** Línea de tiempo horizontal: la cámara viaja de un hito a otro según la narración. */
const EscenaLinea: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const H = d.hitos;
	const PASO = 640; // distancia entre hitos en el lienzo
	const Y = 900;
	// cámara: centrada en el hito que toca
	let x = 0;
	for (let i = 0; i < H.length; i++) x = lerp(x, i * PASO, suave((t - H[i].t + 0.1) / 0.8));
	const camara = `translateX(${ANCHO / 2 - x - 0}px)`;
	return (
		<AbsoluteFill style={{background: FONDO, overflow: 'hidden'}}>
			<div style={{position: 'absolute', left: 0, top: 0, width: ANCHO, height: ALTO, transform: camara}}>
				<svg width={PASO * H.length + 400} height={ALTO} style={{position: 'absolute', left: -200, top: 0, overflow: 'visible'}}>
					<line x1={0} y1={Y + 55} x2={200 + PASO * (H.length - 1) * Math.min(rampa(t, H[0].t, (H[H.length - 1].t - H[0].t) + 0.5), 1) + 200} y2={Y + 55} stroke="rgba(255,255,255,0.3)" strokeWidth={6} strokeDasharray="4 16" strokeLinecap="round" />
				</svg>
				{H.map((h, i) => {
					const e = pop(t, h.t - 0.1, 0.45);
					const activo = i === H.length - 1 ? t >= h.t - 0.1 : t >= h.t - 0.1 && t < H[i + 1].t - 0.1;
					const eFrase = h.frase ? pop(t, (i === H.length - 1 ? (d.t.pregunta - 1.8) : h.t + 0.6), 0.4) : 0;
					return (
						<div key={i} style={{position: 'absolute', left: i * PASO - 260, top: Y - 260, width: 520, textAlign: 'center', opacity: Math.min(e * 1.5, 1) * (activo ? 1 : 0.2), transform: `scale(${(0.7 + 0.3 * e) * (activo ? 1 : 0.85)})`}}>
							<div style={{height: 300, display: 'flex', alignItems: 'flex-end', justifyContent: 'center'}}>
								<Icono tipo={h.icono} tam={h.icono === 'estela' ? 300 : 220} />
							</div>
							<div style={{marginTop: 60, fontFamily: INTER, fontWeight: 900, fontSize: 56, color: activo ? AMARILLO : '#fff', letterSpacing: -1}}>{h.titulo}</div>
							<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 34, color: 'rgba(255,255,255,0.65)'}}>{h.sub}</div>
							{h.frase && activo && (
								<div style={{marginTop: 34, fontFamily: INTER, fontWeight: 800, fontSize: 52, lineHeight: 1.12, color: '#fff', opacity: Math.min(eFrase * 1.5, 1), transform: `translateY(${30 * (1 - eFrase)}px)`}}>«{h.frase}»</div>
							)}
							<div style={{position: 'absolute', left: 250, top: 305, width: 20, height: 20, borderRadius: 10, background: activo ? AMARILLO : '#fff'}} />
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

const EscenaPregunta: React.FC<{d: DatosOrigen; t: number}> = ({d, t}) => {
	const T = d.t;
	const tarjeta = (txt: string, n: string, i: number) => {
		const e = pop(t, T.pregunta + 0.5 + i * 0.25, 0.4);
		const brilla = Math.sin((t - T.pregunta) * 3.2 + i * Math.PI) > 0.3;
		return (
			<div key={n} style={{display: 'flex', alignItems: 'center', gap: 26, width: 820, padding: '30px 36px', borderRadius: 28, background: '#161616', border: `4px solid ${brilla ? AMARILLO : 'rgba(255,255,255,0.18)'}`, opacity: Math.min(e * 1.5, 1), transform: `translateX(${(i ? 1 : -1) * 120 * (1 - e)}px)`}}>
				<span style={{width: 84, height: 84, flex: 'none', borderRadius: 42, background: AMARILLO, color: '#111', fontFamily: INTER, fontWeight: 900, fontSize: 52, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{n}</span>
				<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 54, color: '#fff', textAlign: 'left'}}>{txt}</span>
			</div>
		);
	};
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{width: 940, textAlign: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 104, lineHeight: 1.08, letterSpacing: -3, color: '#fff', marginBottom: 70}}>
				<Palabras txt={d.pregunta} t={t} t0={T.pregunta - 0.05} paso={0.12} tam={104} />
			</div>
			<div style={{display: 'flex', flexDirection: 'column', gap: 30}}>
				{tarjeta(d.opciones[0], '1', 0)}
				{tarjeta(d.opciones[1], '2', 1)}
			</div>
			<div style={{marginTop: 60, fontFamily: INTER, fontWeight: 700, fontSize: 40, color: 'rgba(255,255,255,0.75)', opacity: rampa(t, T.pregunta + 1.2, 0.4)}}>Escribe 1 o 2 en comentarios</div>
		</AbsoluteFill>
	);
};

export const Origen: React.FC<DatosOrigen> = (d) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const T = d.t;
	const fin = d.voz.dur + COLA;
	const salida = rampa(t, fin - 0.3, 0.3);
	const escenas: [number, number, React.FC<{d: DatosOrigen; t: number}>][] = [
		[0, T.mapa, EscenaGancho],
		[T.mapa, T.ley, EscenaMapa],
		[T.ley, T.idea, EscenaLey],
		[T.idea, T.linea, EscenaIdea],
		[T.linea, T.pregunta, EscenaLinea],
		[T.pregunta, fin + 1, EscenaPregunta],
	];
	const sfx = [
		{t: d.gancho.tB - 0.2, s: 'golpe', v: 0.8},
		{t: T.anios - 0.05, s: 'pop', v: 0.4},
		{t: T.ley + 0.55, s: 'golpe', v: 0.5},
		{t: T.ley2 + 0.45, s: 'golpe', v: 0.5},
		{t: T.idea + 1.3, s: 'golpe', v: 0.6},
		{t: T.pregunta - 0.25, s: 'whoosh', v: 0.18},
	];
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<AbsoluteFill style={{opacity: 1 - salida}}>
				{escenas.map(([a, b, E], i) =>
					t >= a - 0.25 && t < b + 0.35 ? (
						<Entra key={i} t={t} t0={a - 0.25}>
							<E d={d} t={t} />
						</Entra>
					) : null,
				)}
			</AbsoluteFill>
			<Audio src={staticFile(d.voz.archivo)} />
			<Audio src={staticFile(d.musica)} volume={(f) => 0.12 * (1 - rampa(f / FPS, fin - 0.6, 0.6))} />
			{sfx.map((x, i) => (
				<Sequence key={i} from={Math.max(0, Math.round(x.t * FPS))} durationInFrames={45}>
					<Audio src={staticFile(`sfx/${x.s}.wav`)} volume={x.v} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};
