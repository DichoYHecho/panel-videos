/**
 * Formato «¿Lo dijo o no lo dijo?» (prototipo v2, fase 2, 27 nov 2026). Estilo minimalista y por escenas:
 * 1) gancho «¿Sabías que…?» en tipografía cinética sobre negro; 2) la cita sobre la foto, palabra a palabra;
 * 3) veredicto FALSO (o VERDADERO) con golpe; 4) el origen real como esquema (nodos y conector);
 * 5) la pregunta para comentar, sola y centrada. Sin fuentes en pantalla (van en la descripción).
 * Los tiempos de cada escena vienen en `t` (medidos sobre la voz); las palabras de la cita, de Whisper.
 */
import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {AMARILLO, FPS, INTER, ROJO, VERDE, lerp, pop, rampa, suave} from './base';
import {Cierre} from './cierre';

export type Palabra = {w: string; a: number; b: number};
export type DatosLoDijo = {
	foto: string; // foto grande (escena de la cita)
	foco: [number, number];
	fotoNodo: string; // segunda foto (nodo del esquema)
	autor: string;
	cita: string; // con *palabras clave*
	veredicto: 'falso' | 'verdadero';
	voz: {archivo: string; dur: number; palabras: Palabra[]};
	musica: string;
	citaIdx: [number, number]; // índices de la cita en voz.palabras
	gancho: {a: string; b: string; tB: number}; // «¿Sabías que esta frase de Einstein…» / «…nunca la dijo Einstein?»
	// tiempos (s) medidos sobre la voz: cuándo empieza cada idea; la cámara del esquema los sigue
	t: {cita: number; veredicto: number; origen: number; anio: number; doc: number; autorNodo: number; vida0: number; vida1: number; murio: number; anios: number; pregunta: number};
	origen: {anio: number; doc: string; docSub: string; nace: number; muere: number};
	pregunta: string; // con *palabra clave*
};

const ANCHO = 1080;
const ALTO = 1920;
const COLA = 2.8; // ~2,5 s de cierre (Comenta, Me gusta, Síguenos) tras la voz
const FONDO = '#0a0a0a';

export const duracionLoDijo = (d: DatosLoDijo) => Math.round((d.voz.dur + COLA) * FPS);

export const Palabras: React.FC<{txt: string; t: number; t0: number; paso: number; tam: number; color?: string; clave?: string}> = ({txt, t, t0, paso, tam, color = '#fff', clave}) => (
	<>
		{txt.split(' ').map((w, i) => {
			const e = pop(t, t0 + i * paso, 0.32);
			const esClave = clave && w.replace(/[¿?.,…]/g, '') === clave;
			return (
				<span key={i} style={{display: 'inline-block', margin: `0 ${tam * 0.14}px`, opacity: Math.min(e * 1.8, 1), transform: `translateY(${tam * 0.45 * (1 - e)}px)`, color: esClave ? AMARILLO : color}}>
					{w}
				</span>
			);
		})}
	</>
);

/** Escena 1: gancho en dos golpes sobre negro, con un leve zoom continuo. */
const EscenaGancho: React.FC<{d: DatosLoDijo; t: number}> = ({d, t}) => {
	const punch = t > d.gancho.tB - 0.05 ? 1 + 0.06 * (1 - suave((t - d.gancho.tB + 0.05) / 0.35)) : 1;
	const zoom = (1 + 0.04 * (t / d.t.cita)) * punch;
	const apellido = d.autor.split(' ').slice(-1)[0];
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{position: 'absolute', width: 900, height: 900, borderRadius: '50%', background: 'radial-gradient(circle, rgba(245,197,24,0.10), transparent 65%)', transform: `scale(${1 + 0.15 * Math.sin(t * 1.3)})`}} />
			<div style={{width: 900, textAlign: 'center', fontFamily: INTER, fontWeight: 800, letterSpacing: -2, lineHeight: 1.1, transform: `scale(${zoom})`}}>
				<div style={{fontSize: 84, color: 'rgba(255,255,255,0.92)'}}>
					<Palabras txt={d.gancho.a} t={t} t0={0} paso={0.17} tam={84} clave={apellido} />
				</div>
				<div style={{fontSize: 118, fontWeight: 900, marginTop: 26}}>
					<Palabras txt={d.gancho.b} t={t} t0={d.gancho.tB} paso={0.2} tam={118} color={AMARILLO} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

/** Escena 2 y 3: la foto con movimiento de cámara, la cita palabra a palabra y el veredicto. */
const EscenaCita: React.FC<{d: DatosLoDijo; t: number}> = ({d, t}) => {
	const T = d.t;
	const P = d.voz.palabras.slice(d.citaIdx[0], d.citaIdx[1] + 1);
	const palabras = d.cita.split(' ');
	const falso = d.veredicto === 'falso';
	const golpe = rampa(t, T.veredicto, 0.05);
	const k = (t - T.cita) / (T.origen - T.cita);
	const pan = lerp(0, -140, suave(Math.min(k, 1))); // la cámara baja despacio por la cara
	const zoom = lerp(1.12, 1.28, Math.min(k, 1)) + (t > T.veredicto ? 0.08 * (1 - suave((t - T.veredicto) / 0.4)) : 0);
	const tiembla = t > T.veredicto && t < T.veredicto + 0.35 ? Math.sin(t * 90) * 10 * (1 - (t - T.veredicto) / 0.35) : 0;
	const gris = falso ? golpe : 0;
	const destello = t > T.veredicto ? Math.max(0, 1 - (t - T.veredicto) / 0.25) : 0;
	const eSello = suave(Math.min(Math.max((t - T.veredicto) / 0.2, 0), 1));
	const tachado = falso ? rampa(t, T.veredicto + 0.2, 0.4) : 0;
	const color = falso ? ROJO : VERDE;
	return (
		<AbsoluteFill style={{background: FONDO, transform: `translateX(${tiembla}px)`}}>
			<AbsoluteFill style={{transform: `translateY(${pan}px) scale(${zoom})`, transformOrigin: '50% 35%'}}>
				<Img src={staticFile(d.foto)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${d.foco[0] * 100}% ${d.foco[1] * 100}%`, filter: `grayscale(${0.6 + 0.4 * gris}) contrast(1.1) brightness(${lerp(0.62, 0.42, gris)})`}} />
			</AbsoluteFill>
			<AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(10,10,10,0.35) 0%, rgba(10,10,10,0.15) 30%, rgba(10,10,10,0.85) 62%, #0a0a0a 100%)'}} />
			<AbsoluteFill style={{background: color, opacity: destello * 0.35, mixBlendMode: 'screen'}} />

			{/* la cita: cada palabra aparece al decirla; las claves en amarillo */}
			<div style={{position: 'absolute', top: 1080, left: 80, width: 840, fontFamily: INTER, fontWeight: 700, fontSize: 64, lineHeight: 1.18, letterSpacing: -1, color: '#fff', opacity: lerp(1, 0.35, golpe)}}>
				{palabras.map((w, i) => {
					const a = (P[i]?.a ?? T.cita + i * 0.3) - 0.05;
					const e = rampa(t, a, 0.25);
					const clave = w.includes('*');
					return (
						<span key={i} style={{display: 'inline-block', marginRight: 16, opacity: lerp(0.0, 1, e), transform: `translateY(${18 * (1 - e)}px)`, color: clave ? AMARILLO : undefined}}>
							{w.replace(/\*/g, '')}
						</span>
					);
				})}
				<div style={{marginTop: 34, fontSize: 40, fontWeight: 800, letterSpacing: 3, color: AMARILLO, textTransform: 'uppercase', opacity: rampa(t, T.cita + 0.3, 0.4)}}>
					<span style={{position: 'relative'}}>
						{d.autor}
						<span style={{position: 'absolute', left: -8, top: '50%', height: 7, background: ROJO, width: `calc(${tachado * 100}% + 16px)`}} />
					</span>
				</div>
			</div>

			{/* veredicto */}
			{t > T.veredicto - 0.02 && (
				<div style={{position: 'absolute', left: ANCHO / 2, top: 760, transform: `translate(-50%, -50%) scale(${lerp(1.8, 1, eSello)}) rotate(${lerp(0, -6, eSello)}deg)`, opacity: Math.min(eSello * 2, 1), border: `10px solid ${color}`, borderRadius: 18, padding: '14px 46px 6px', fontFamily: INTER, fontWeight: 900, fontSize: 150, letterSpacing: 8, color}}>
					{falso ? 'FALSO' : 'VERDADERO'}
				</div>
			)}
		</AbsoluteFill>
	);
};

/**
 * Escena 4: el origen como esquema en un «lienzo» más grande que la pantalla. La cámara va al nodo del que se
 * habla: primero el documento donde aparece la frase (y el año), después el autor y su barra de vida, y al final
 * se aleja para enseñar todo: la vida del autor termina antes de que aparezca la frase.
 */
const EscenaOrigen: React.FC<{d: DatosLoDijo; t: number}> = ({d, t}) => {
	const T = d.t;
	const O = d.origen;
	// eje de años del lienzo
	const y0 = Math.floor((O.nace - 10) / 10) * 10;
	const y1 = Math.ceil((O.anio + 10) / 10) * 10;
	const X = (a: number) => 90 + ((a - y0) / (y1 - y0)) * 900;
	const EJE = 1180;
	const doc = {x: Math.min(X(O.anio), 800), y: 760};
	const aut = {x: 300, y: 760};

	// cámara: [tiempo, foco x, foco y, zoom]
	const claves: [number, number, number, number][] = [
		[T.origen, doc.x, 820, 1.5],
		[T.autorNodo, aut.x, 860, 1.45],
		[T.vida0, (X(O.nace) + X(O.muere)) / 2, 1020, 1.1],
		[T.murio, 560, 860, 1.0],
	];
	let cam = claves[0];
	for (let i = 1; i < claves.length; i++) {
		const [ti] = claves[i];
		const k = suave((t - ti + 0.1) / 0.8);
		if (k <= 0) break;
		const p = cam;
		cam = [ti, lerp(p[1], claves[i][1], k), lerp(p[2], claves[i][2], k), lerp(p[3], claves[i][3], k)];
	}
	const [, fx, fy, s] = cam;
	const camara = `translate(${ANCHO / 2 - fx * s}px, ${ALTO / 2 - fy * s}px) scale(${s})`;

	const eDoc = pop(t, T.origen - 0.05, 0.45);
	const eAnio = pop(t, T.anio - 0.05, 0.4);
	const eDocTxt = rampa(t, T.doc - 0.1, 0.4);
	const eAut = pop(t, T.autorNodo - 0.05, 0.45);
	const eEje = rampa(t, T.autorNodo + 0.3, 0.6);
	const vida = rampa(t, T.vida0 - 0.05, Math.max(T.vida1 - T.vida0 + 0.3, 0.5)); // la barra crece mientras lo dice
	const eHueco = rampa(t, T.murio - 0.05, 0.7);
	const eAnios = pop(t, T.anios - 0.05, 0.4);
	const texto = (txt: string | number, x: number, y: number, tam: number, color: string, op: number, peso = 800) => (
		<text x={x} y={y} fill={color} opacity={op} fontFamily={INTER} fontWeight={peso} fontSize={tam} textAnchor="middle">{txt}</text>
	);

	return (
		<AbsoluteFill style={{background: FONDO, overflow: 'hidden'}}>
			<div style={{position: 'absolute', left: 0, top: 0, width: ANCHO, height: ALTO, transformOrigin: '0 0', transform: camara}}>
				<svg width={ANCHO} height={ALTO} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
					{/* rejilla de puntos: pizarra */}
					{Array.from({length: 14 * 22}, (_, i) => (
						<circle key={i} cx={-90 + (i % 14) * 90} cy={-40 + Math.floor(i / 14) * 95} r={2} fill="rgba(255,255,255,0.08)" />
					))}
					{/* conectores de los nodos al eje */}
					<line x1={doc.x} y1={doc.y + 190} x2={lerp(doc.x, X(O.anio), eEje)} y2={lerp(doc.y + 190, EJE, eEje)} stroke="rgba(255,255,255,0.4)" strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" />
					<line x1={aut.x} y1={aut.y + 210} x2={aut.x} y2={lerp(aut.y + 210, EJE, eEje)} stroke="rgba(255,255,255,0.4)" strokeWidth={4} strokeDasharray="3 12" strokeLinecap="round" />
					{/* eje del tiempo */}
					<line x1={X(y0)} y1={EJE} x2={lerp(X(y0), X(y1), eEje)} y2={EJE} stroke="rgba(255,255,255,0.25)" strokeWidth={4} strokeLinecap="round" />
					{/* vida del autor */}
					<rect x={X(O.nace)} y={EJE - 14} width={(X(O.muere) - X(O.nace)) * vida} height={28} rx={14} fill={AMARILLO} />
					{texto(O.nace, X(O.nace), EJE + 78, 44, '#fff', rampa(t, T.vida0, 0.3))}
					{texto(O.muere, X(O.muere), EJE + 78, 44, '#fff', rampa(t, T.vida1 - 0.1, 0.3))}
					{texto('vida', (X(O.nace) + X(O.muere)) / 2, EJE - 36, 30, 'rgba(255,255,255,0.6)', vida, 700)}
					{/* hueco entre la muerte y la frase */}
					<line x1={X(O.muere)} y1={EJE} x2={lerp(X(O.muere), X(O.anio), eHueco)} y2={EJE} opacity={eHueco > 0.01 ? 1 : 0} stroke={ROJO} strokeWidth={8} strokeDasharray="10 12" strokeLinecap="round" />
					<circle cx={X(O.anio)} cy={EJE} r={16 * eEje} fill={AMARILLO} stroke="#111" strokeWidth={3} />
					{texto(O.anio, X(O.anio), EJE + 78, 44, AMARILLO, eEje)}
				</svg>

				{/* nodo documento, con el año encima */}
				<div style={{position: 'absolute', left: doc.x - 230, top: doc.y - 330, width: 460, textAlign: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 130, letterSpacing: -4, color: AMARILLO, opacity: Math.min(eAnio * 1.6, 1), transform: `translateY(${40 * (1 - eAnio)}px)`}}>
					{O.anio}
				</div>
				<div style={{position: 'absolute', left: doc.x - 230, top: doc.y - 170, width: 460, height: 360, borderRadius: 30, background: '#161616', border: '2px solid rgba(255,255,255,0.18)', opacity: Math.min(eDoc * 1.5, 1), transform: `scale(${0.7 + 0.3 * eDoc})`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12}}>
					<svg width={110} height={134} viewBox="0 0 90 110">
						<path d="M8 4h52l24 24v76a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4z" fill="none" stroke="#fff" strokeWidth={5} />
						<path d="M60 4v24h24" fill="none" stroke="#fff" strokeWidth={5} />
						{[46, 62, 78].map((y) => (
							<line key={y} x1={20} y1={y} x2={lerp(20, 68, rampa(t, T.origen + 0.3 + y / 300, 0.3))} y2={y} stroke={AMARILLO} strokeWidth={5} strokeLinecap="round" />
						))}
					</svg>
					<div style={{opacity: eDocTxt, textAlign: 'center'}}>
						<div style={{fontFamily: INTER, fontWeight: 800, fontSize: 46, color: '#fff', lineHeight: 1.1}}>{O.doc}</div>
						<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 32, color: 'rgba(255,255,255,0.6)', marginTop: 6}}>{O.docSub}</div>
					</div>
				</div>

				{/* nodo autor */}
				<div style={{position: 'absolute', left: aut.x - 150, top: aut.y - 170, width: 300, textAlign: 'center', opacity: Math.min(eAut * 1.5, 1), transform: `scale(${0.7 + 0.3 * eAut})`}}>
					<Img src={staticFile(d.fotoNodo)} style={{width: 300, height: 300, borderRadius: '50%', objectFit: 'cover', objectPosition: '50% 30%', filter: 'grayscale(1) brightness(0.85)', border: `5px solid ${AMARILLO}`}} />
					<div style={{marginTop: 14, fontFamily: INTER, fontWeight: 800, fontSize: 42, color: '#fff'}}>{d.autor.split(' ').slice(-1)[0]}</div>
				</div>

				{/* años de diferencia, sobre el hueco rojo */}
				<div style={{position: 'absolute', left: (X(O.muere) + X(O.anio)) / 2 - 160, top: EJE - 150, width: 320, textAlign: 'center', opacity: Math.min(eAnios * 1.6, 1), transform: `scale(${0.6 + 0.4 * eAnios})`}}>
					<span style={{display: 'inline-block', background: ROJO, color: '#fff', fontFamily: INTER, fontWeight: 900, fontSize: 44, padding: '10px 26px', borderRadius: 50, whiteSpace: 'nowrap'}}>
						{O.anio - O.muere} años después
					</span>
				</div>
			</div>
		</AbsoluteFill>
	);
};

/** Escena 5: la pregunta, sola y centrada. */
const EscenaPregunta: React.FC<{d: DatosLoDijo; t: number}> = ({d, t}) => {
	const T = d.t;
	const zoom = 1 + 0.05 * suave((t - T.pregunta) / 2.5);
	const eSub = rampa(t, T.pregunta + 0.9, 0.4);
	const palabras = d.pregunta.split(' ');
	return (
		<AbsoluteFill style={{background: FONDO, alignItems: 'center', justifyContent: 'center'}}>
			<div style={{width: 900, textAlign: 'center', fontFamily: INTER, fontWeight: 900, fontSize: 112, lineHeight: 1.08, letterSpacing: -3, color: '#fff', transform: `scale(${zoom})`}}>
				{palabras.map((w, i) => {
					const e = pop(t, T.pregunta - 0.05 + i * 0.12, 0.32);
					return (
						<span key={i} style={{display: 'inline-block', margin: '0 14px', opacity: Math.min(e * 1.8, 1), transform: `translateY(${50 * (1 - e)}px)`, color: w.includes('*') ? AMARILLO : undefined}}>
							{w.replace(/\*/g, '')}
						</span>
					);
				})}
				<div style={{marginTop: 50, fontSize: 40, fontWeight: 700, letterSpacing: 0, color: 'rgba(255,255,255,0.7)', opacity: eSub}}>Cuéntalo en comentarios</div>
				<Cierre t={t} t0={d.voz.dur - 0.1} />
			</div>
		</AbsoluteFill>
	);
};

/** Transición: la escena entrante sube y aparece en `dur` segundos. */
export const Entra: React.FC<{t: number; t0: number; dur?: number; children: React.ReactNode}> = ({t, t0, dur = 0.35, children}) => {
	const e = suave((t - t0) / dur);
	return <AbsoluteFill style={{opacity: e, transform: `translateY(${80 * (1 - e)}px) scale(${lerp(1.04, 1, e)})`}}>{children}</AbsoluteFill>;
};

export const LoDijo: React.FC<DatosLoDijo> = (d) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const T = d.t;
	const fin = d.voz.dur + COLA;
	const salida = rampa(t, fin - 0.3, 0.3); // a negro: enlaza con el inicio (bucle)

	const sfx = [
		{t: d.gancho.tB - 0.2, s: 'golpe', v: 0.8}, // tambor en la pausa, antes de «nunca la dijo»
		{t: T.veredicto - 0.03, s: 'golpe', v: 1},
		{t: T.origen - 0.25, s: 'whoosh', v: 0.18},
		{t: T.anios - 0.05, s: 'pop', v: 0.5},
		{t: T.pregunta - 0.25, s: 'whoosh', v: 0.18},
	];

	return (
		<AbsoluteFill style={{background: FONDO}}>
			<AbsoluteFill style={{opacity: 1 - salida}}>
				{t < T.cita + 0.4 && <EscenaGancho d={d} t={t} />}
				{t >= T.cita - 0.15 && t < T.origen + 0.4 && (
					<Entra t={t} t0={T.cita - 0.15}>
						<EscenaCita d={d} t={t} />
					</Entra>
				)}
				{t >= T.origen - 0.2 && t < T.pregunta + 0.4 && (
					<Entra t={t} t0={T.origen - 0.2}>
						<EscenaOrigen d={d} t={t} />
					</Entra>
				)}
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
