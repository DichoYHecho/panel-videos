/**
 * Formato «Autor contra autor» (prototipo v1, fase 2, 27 nov 2026). Dos frases reales que dicen lo contrario
 * sobre el mismo tema. Mismo estilo minimalista por escenas que «¿Lo dijo o no lo dijo?»:
 * 1) gancho «¿Sabías que…?» sobre negro; 2) pantalla partida en diagonal con «VS»; 3) la frase de A a pantalla
 * completa; 4) la frase de B (cortinilla diagonal); 5) la pregunta, centrada, con los dos retratos para votar.
 * Sin ganador y sin fuentes en pantalla (van en la descripción).
 */
import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {AMARILLO, FPS, INTER, lerp, pop, rampa, suave} from './base';
import {Entra, Palabras, type Palabra} from './LoDijo';
import {Cierre} from './cierre';

type Autor = {nombre: string; foto: string; foco: [number, number]; epoca: string; cita: string; citaIdx: [number, number]; desfase?: number};
export type DatosContra = {
	tema: string;
	a: Autor;
	b: Autor;
	voz: {archivo: string; dur: number; palabras: Palabra[]};
	musica: string;
	gancho: {a: string; b: string; tB: number};
	t: {vs: number; nombreA: number; citaA: number; nombreB: number; citaB: number; pregunta: number};
	pregunta: string;
	cierre: string;
};

const ANCHO = 1080;
const ALTO = 1920;
const COLA = 2.8; // ~2,5 s de cierre (Comenta, Me gusta, Síguenos) tras la voz
const FONDO = '#0a0a0a';

export const duracionContra = (d: DatosContra) => Math.round((d.voz.dur + COLA) * FPS);

const Foto: React.FC<{a: Autor; zoom: number; gris?: number; brillo?: number}> = ({a, zoom, gris = 0.35, brillo = 0.7}) => (
	<AbsoluteFill style={{transform: `scale(${zoom})`, transformOrigin: `${a.foco[0] * 100}% ${a.foco[1] * 100}%`}}>
		<Img src={staticFile(a.foto)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${a.foco[0] * 100}% ${a.foco[1] * 100}%`, filter: `grayscale(${gris}) contrast(1.08) brightness(${brillo})`}} />
	</AbsoluteFill>
);

/** Escena 1: gancho sobre negro. */
const EscenaGancho: React.FC<{d: DatosContra; t: number}> = ({d, t}) => {
	const punch = t > d.gancho.tB - 0.05 ? 1 + 0.06 * (1 - suave((t - d.gancho.tB + 0.05) / 0.35)) : 1;
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{position: 'absolute', width: 900, height: 900, borderRadius: '50%', background: 'radial-gradient(circle, rgba(245,197,24,0.10), transparent 65%)', transform: `scale(${1 + 0.15 * Math.sin(t * 1.3)})`}} />
			<div style={{width: 900, textAlign: 'center', fontFamily: INTER, fontWeight: 800, letterSpacing: -2, lineHeight: 1.1, transform: `scale(${(1 + 0.04 * (t / d.t.vs)) * punch})`}}>
				<div style={{fontSize: 80, color: 'rgba(255,255,255,0.92)'}}>
					<Palabras txt={d.gancho.a} t={t} t0={0} paso={0.16} tam={80} clave={d.tema.split(' ').slice(-1)[0].toLowerCase()} />
				</div>
				<div style={{fontSize: 116, fontWeight: 900, marginTop: 26}}>
					<Palabras txt={d.gancho.b} t={t} t0={d.gancho.tB} paso={0.2} tam={116} color={AMARILLO} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

/** Escena 2: pantalla partida en diagonal; cada mitad entra por su lado y el «VS» cae en medio. */
const EscenaVS: React.FC<{d: DatosContra; t: number}> = ({d, t}) => {
	const T = d.t;
	const eA = suave((t - T.vs) / 0.45);
	const eB = suave((t - T.vs - 0.12) / 0.45);
	const eVS = pop(t, T.vs + 0.35, 0.35);
	const enfoqueA = rampa(t, T.nombreA - 0.1, 0.4); // al decir el primer nombre, su mitad se ilumina
	const mitad = (lado: 'a' | 'b', e: number) => {
		const au = d[lado];
		const izq = lado === 'a';
		const clip = izq ? 'polygon(0 0, 100% 0, 0 100%)' : 'polygon(100% 0, 100% 100%, 0 100%)';
		const luz = izq ? lerp(0.6, 0.85, enfoqueA) : lerp(0.6, 0.35, enfoqueA);
		return (
			<AbsoluteFill style={{clipPath: clip, transform: `translateX(${(izq ? -1 : 1) * 700 * (1 - e)}px)`}}>
				{/* cada foto se desplaza para que la cara caiga dentro de su triángulo */}
				<AbsoluteFill style={{left: izq ? -220 : 260, top: izq ? -140 : 520}}>
					<Foto a={au} zoom={1.05 + 0.05 * rampa(t, T.vs, 3)} brillo={luz} />
				</AbsoluteFill>
				<div style={{position: 'absolute', [izq ? 'left' : 'right']: 70, [izq ? 'top' : 'bottom']: izq ? 260 : 330, textAlign: izq ? 'left' : 'right', fontFamily: INTER}}>
					<div style={{fontSize: 70, fontWeight: 900, color: '#fff', letterSpacing: -1, textShadow: '0 4px 30px rgba(0,0,0,0.9)'}}>{au.nombre}</div>
					<div style={{display: 'inline-block', marginTop: 8, fontSize: 30, fontWeight: 800, color: '#111', background: AMARILLO, padding: '6px 14px', borderRadius: 8, letterSpacing: 2, textTransform: 'uppercase'}}>{au.epoca}</div>
				</div>
			</AbsoluteFill>
		);
	};
	return (
		<AbsoluteFill style={{background: FONDO}}>
			{mitad('a', eA)}
			{mitad('b', eB)}
			<svg width={ANCHO} height={ALTO} style={{position: 'absolute', inset: 0}}>
				<line x1={ANCHO} y1={0} x2={lerp(ANCHO, 0, eB)} y2={lerp(0, ALTO, eB)} stroke={AMARILLO} strokeWidth={6} />
			</svg>
			<div style={{position: 'absolute', left: ANCHO / 2, top: ALTO / 2, transform: `translate(-50%, -50%) scale(${lerp(2.2, 1, eVS)})`, opacity: Math.min(eVS * 2, 1), width: 230, height: 230, borderRadius: '50%', background: AMARILLO, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 110, color: '#111', letterSpacing: -4, boxShadow: '0 0 60px rgba(245,197,24,0.5)'}}>
				VS
			</div>
			<div style={{position: 'absolute', top: 120, width: ANCHO, textAlign: 'center', opacity: rampa(t, T.vs + 0.5, 0.4)}}>
				<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 32, letterSpacing: 4, color: '#111', background: '#fff', padding: '10px 24px', borderRadius: 10, textTransform: 'uppercase'}}>{d.tema}</span>
			</div>
		</AbsoluteFill>
	);
};

/** Escenas 3 y 4: la frase de un autor a pantalla completa; las palabras aparecen al decirlas. */
const EscenaCita: React.FC<{d: DatosContra; lado: 'a' | 'b'; t: number; t0: number; t1: number}> = ({d, lado, t, t0, t1}) => {
	const au = d[lado];
	const P = d.voz.palabras.slice(au.citaIdx[0], au.citaIdx[1] + 1);
	const palabras = au.cita.split(' ');
	const k = suave(Math.min(Math.max((t - t0) / (t1 - t0), 0), 1));
	const desplaza = lado === 'a' ? lerp(40, -40, k) : lerp(-40, 40, k); // la cámara se mueve en sentidos opuestos
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<AbsoluteFill style={{transform: `translateX(${desplaza}px)`}}>
				<Foto a={au} zoom={lerp(1.15, 1.3, k)} brillo={0.55} />
			</AbsoluteFill>
			<AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(10,10,10,0.5) 0%, rgba(10,10,10,0.1) 28%, rgba(10,10,10,0.85) 58%, #0a0a0a 100%)'}} />
			<div style={{position: 'absolute', top: 130, left: 70, display: 'flex', alignItems: 'center', gap: 16, opacity: rampa(t, t0, 0.4)}}>
				<span style={{fontFamily: INTER, fontWeight: 900, fontSize: 30, color: '#111', background: AMARILLO, padding: '8px 18px', borderRadius: 8}}>{lado === 'a' ? '1' : '2'}</span>
				<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 44, color: '#fff'}}>{au.nombre}</span>
				<span style={{fontFamily: INTER, fontWeight: 600, fontSize: 30, color: 'rgba(255,255,255,0.6)'}}>{au.epoca}</span>
			</div>
			<div style={{position: 'absolute', top: 1060, left: 80, width: 840, fontFamily: INTER, fontWeight: 700, fontSize: palabras.length > 10 ? 64 : 92, lineHeight: 1.16, letterSpacing: -1, color: '#fff'}}>
				<span style={{color: AMARILLO, fontWeight: 900}}>«</span>
				{palabras.map((w, i) => {
					const a = (P[i]?.a ?? t0 + i * 0.3) + (au.desfase ?? 0) - 0.05;
					const e = rampa(t, a, 0.25);
					return (
						<span key={i} style={{display: 'inline-block', marginRight: 16, opacity: e, transform: `translateY(${18 * (1 - e)}px)`, color: w.includes('*') ? AMARILLO : undefined}}>
							{w.replace(/\*/g, '')}
						</span>
					);
				})}
				<span style={{color: AMARILLO, fontWeight: 900, opacity: rampa(t, P[P.length - 1].b + (au.desfase ?? 0), 0.3)}}>»</span>
			</div>
		</AbsoluteFill>
	);
};

/**
 * Escena 5: la pregunta arriba y, debajo, una balanza con los dos autores (1 y 2) en los platillos. La balanza
 * se inclina hacia uno y hacia otro, como si no se decidiera, y un bocadillo pide «Escribe 1 o 2».
 */
const EscenaPregunta: React.FC<{d: DatosContra; t: number}> = ({d, t}) => {
	const T = d.t;
	const t0 = T.pregunta;
	const eBal = pop(t, t0 + 0.2, 0.5);
	const eBoc = pop(t, t0 + 1.1, 0.45);
	// inclinación: entra hacia A, luego oscila A/B; amortiguado para que no maree
	const u = Math.max(t - t0 - 0.4, 0);
	const angulo = 9 * Math.sin(u * 3.2) * (0.55 + 0.45 * Math.exp(-u * 0.8));
	const rad = (angulo * Math.PI) / 180;
	const CX = ANCHO / 2;
	const CY = 880; // pivote
	const L = 330; // media viga
	const cuerda = 150;
	const extremo = (s: number) => ({x: CX + s * L * Math.cos(rad), y: CY + s * L * Math.sin(rad)});
	const platillo = (a: Autor, s: number, n: string) => {
		const p = extremo(s);
		const ganando = s * angulo > 2; // el platillo que baja se ilumina
		return (
			<div key={n} style={{position: 'absolute', left: p.x - 120, top: p.y + cuerda, width: 240, textAlign: 'center'}}>
				<div style={{position: 'relative', width: 240, height: 240, borderRadius: '50%', overflow: 'hidden', border: `7px solid ${ganando ? AMARILLO : 'rgba(255,255,255,0.35)'}`, boxShadow: ganando ? '0 0 40px rgba(245,197,24,0.45)' : 'none'}}>
					<Foto a={a} zoom={1.25} brillo={ganando ? 0.95 : 0.6} />
				</div>
				<div style={{position: 'absolute', top: -18, left: -6, width: 70, height: 70, borderRadius: '50%', background: AMARILLO, color: '#111', fontFamily: INTER, fontWeight: 900, fontSize: 44, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{n}</div>
				<div style={{marginTop: 14, fontFamily: INTER, fontWeight: 800, fontSize: 40, color: '#fff'}}>{a.nombre}</div>
			</div>
		);
	};
	const A = extremo(-1);
	const B = extremo(1);
	const salto = Math.abs(Math.sin((t - t0) * 4)) * 10 * eBoc;
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<div style={{position: 'absolute', top: 250, left: 70, width: 940, textAlign: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 104, lineHeight: 1.08, letterSpacing: -3, color: '#fff'}}>
				<Palabras txt={d.pregunta} t={t} t0={t0 - 0.05} paso={0.12} tam={104} />
			</div>
			<AbsoluteFill style={{opacity: Math.min(eBal * 1.5, 1), transform: `translateY(${120 * (1 - eBal)}px)`}}>
				<svg width={ANCHO} height={ALTO} style={{position: 'absolute', inset: 0}}>
					{/* columna y base */}
					<line x1={CX} y1={CY} x2={CX} y2={CY + 470} stroke="rgba(255,255,255,0.5)" strokeWidth={10} strokeLinecap="round" />
					<rect x={CX - 120} y={CY + 465} width={240} height={16} rx={8} fill="rgba(255,255,255,0.5)" />
					{/* cuerdas */}
					<line x1={A.x} y1={A.y} x2={A.x} y2={A.y + cuerda} stroke="rgba(255,255,255,0.45)" strokeWidth={4} />
					<line x1={B.x} y1={B.y} x2={B.x} y2={B.y + cuerda} stroke="rgba(255,255,255,0.45)" strokeWidth={4} />
					{/* viga */}
					<line x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={AMARILLO} strokeWidth={14} strokeLinecap="round" />
					<circle cx={CX} cy={CY} r={22} fill={AMARILLO} stroke="#111" strokeWidth={4} />
				</svg>
				{platillo(d.a, -1, '1')}
				{platillo(d.b, 1, '2')}
			</AbsoluteFill>
			{/* al acabar la voz, el bocadillo deja paso al cierre */}
			<div style={{position: 'absolute', top: 1370, left: 0, width: ANCHO}}>
				<Cierre t={t} t0={d.voz.dur - 0.1} />
			</div>
			{/* bocadillo para comentar */}
			<div style={{position: 'absolute', top: 1440 - salto, left: 0, width: ANCHO, textAlign: 'center', opacity: Math.min(eBoc * 1.5, 1) * (1 - rampa(t, d.voz.dur - 0.35, 0.3)), transform: `scale(${0.6 + 0.4 * eBoc})`}}>
				<span style={{position: 'relative', display: 'inline-block', background: '#fff', color: '#111', fontFamily: INTER, fontWeight: 900, fontSize: 48, padding: '18px 40px', borderRadius: 40}}>
					Escribe <span style={{color: '#111', background: AMARILLO, borderRadius: 12, padding: '0 14px'}}>1</span> o <span style={{color: '#111', background: AMARILLO, borderRadius: 12, padding: '0 14px'}}>2</span> 💬
					<span style={{position: 'absolute', left: '50%', top: -18, marginLeft: -18, width: 0, height: 0, borderLeft: '18px solid transparent', borderRight: '18px solid transparent', borderBottom: '20px solid #fff'}} />
				</span>
			</div>
		</AbsoluteFill>
	);
};

/** Cortinilla diagonal amarilla entre la frase de A y la de B. */
const Cortinilla: React.FC<{t: number; t0: number}> = ({t, t0}) => {
	const p = (t - t0) / 0.55;
	if (p < 0 || p > 1) return null;
	const x = lerp(-1.4, 1.4, suave(p)) * ANCHO;
	return <div style={{position: 'absolute', top: -300, left: x, width: 700, height: ALTO + 600, background: AMARILLO, transform: 'rotate(18deg)'}} />;
};

export const ContraAutor: React.FC<DatosContra> = (d) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const T = d.t;
	const fin = d.voz.dur + COLA;
	const salida = rampa(t, fin - 0.3, 0.3);
	const cambio = T.nombreB - 0.25; // el cambio de A a B, tapado por la cortinilla
	const sfx = [
		{t: d.gancho.tB - 0.2, s: 'golpe', v: 0.8},
		{t: T.vs + 0.35, s: 'golpe', v: 0.9},
		{t: cambio - 0.2, s: 'whoosh', v: 0.2},
		{t: T.pregunta - 0.25, s: 'whoosh', v: 0.18},
	];
	return (
		<AbsoluteFill style={{background: FONDO}}>
			<AbsoluteFill style={{opacity: 1 - salida}}>
				{t < T.vs + 0.4 && <EscenaGancho d={d} t={t} />}
				{t >= T.vs - 0.1 && t < T.citaA + 0.4 && (
					<Entra t={t} t0={T.vs - 0.1} dur={0.2}>
						<EscenaVS d={d} t={t} />
					</Entra>
				)}
				{t >= T.citaA - 0.3 && t < cambio + 0.1 && (
					<Entra t={t} t0={T.citaA - 0.3}>
						<EscenaCita d={d} lado="a" t={t} t0={T.citaA - 0.3} t1={cambio} />
					</Entra>
				)}
				{t >= cambio && t < T.pregunta + 0.4 && <EscenaCita d={d} lado="b" t={t} t0={cambio} t1={T.pregunta} />}
				<Cortinilla t={t} t0={cambio - 0.27} />
				{t >= T.pregunta - 0.25 && (
					<Entra t={t} t0={T.pregunta - 0.25}>
						<EscenaPregunta d={d} t={t} />
					</Entra>
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
