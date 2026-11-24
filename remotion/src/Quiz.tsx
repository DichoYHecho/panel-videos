/**
 * Short «¿Quién escribió esto?» de Dicho y Hecho (vertical 1080x1920, 30 fps). Los tiempos salen de la voz.
 *
 *   gancho   Comillas que se abren + «¿Quién escribió esto?» grande en el centro. Retrato oculto.
 *   cita     La pregunta sube; la frase se escribe a pluma al ritmo de la voz (letra según su longitud).
 *   opciones Tres tarjetas (A, B, C) entran cuando la voz las nombra + «Comenta: ¿A, B o C?» con cuenta atrás.
 *   revela   ✓ verde / ✕ rojo, barrido de luz y el retrato se enfoca. Ficha: nombre, quién era, mapa del país
 *            con alfiler, línea de vida, chapas (dónde lo dijo y tema) y firma. Sin fuentes ni créditos: van
 *            en la descripción.
 *   suscribe «¿La acertaste?» + botón «Suscríbete» pulsado.
 *   bucle    Comillas que se cierran y todo vuelve al primer fotograma.
 */
import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {AMARILLO, Barrido, FPS, INTER, Retrato, Suscribete, Textura, lerp, pop, rampa} from './base';
import {Chapa, CitaPluma, Comenta, Comillas, LineaVida, MapaPais, MarcoTema, Opciones, TEMAS} from './piezas';
import type {DatosQuiz} from './datos';

const W = 1080;
const H = 1920;
const CX = 530; // algo a la izquierda por los botones de la app

export const tiempos = (d: DatosQuiz) => {
	const G0 = 0.1;
	const C0 = G0 + d.voz.gancho.dur;
	const O0 = C0 + d.voz.cita.dur;
	const finO = O0 + d.voz.opciones.dur;
	const REV = finO + 0.9; // cuenta atrás de «Comenta»
	const A0 = REV + 0.5; // la voz dice el nombre cuando las tarjetas ya se han ido
	const finA = A0 + d.voz.autor.dur;
	const SUS = finA - 0.2;
	const BUCLE = SUS + 2.0;
	const DUR = BUCLE + 0.7;
	return {G0, C0, O0, finO, REV, A0, finA, SUS, BUCLE, DUR};
};
export const duracionQuiz = (d: DatosQuiz) => Math.round(tiempos(d).DUR * FPS);

/** Tamaño de la frase según su longitud (que quepa entre la pregunta y las tarjetas). */
const tamCita = (cita: string) => {
	const n = cita.replace(/\*/g, '').length;
	return n <= 40 ? 100 : n <= 70 ? 88 : n <= 110 ? 76 : n <= 160 ? 66 : n <= 220 ? 58 : 52;
};

export const Quiz: React.FC<DatosQuiz> = (d) => {
	const frame = useCurrentFrame();
	const t = frame / FPS;
	const T = tiempos(d);
	const tema = TEMAS[d.tema] ?? TEMAS.vida;

	const oculto = Math.max(1 - rampa(t, T.REV + 0.15, 0.55), rampa(t, T.BUCLE, 0.5));
	const sube = t < T.BUCLE ? rampa(t, T.C0 - 0.3, 0.45) : 0;
	const preguntaVis = Math.max(1 - rampa(t, T.REV - 0.1, 0.3), rampa(t, T.BUCLE + 0.2, 0.4));
	const citaVis = rampa(t, T.C0 - 0.25, 0.3) * (1 - rampa(t, T.SUS - 0.1, 0.3));
	const tarjetasFuera = rampa(t, T.REV + 0.5, 0.35);
	const citaArriba = rampa(t, T.REV + 0.75, 0.5); // tras revelar, la frase sube sobre el retrato
	const fichaVis = 1 - rampa(t, T.BUCLE - 0.15, 0.35);
	const zoom = 1.04 + 0.06 * Math.sin(Math.PI * Math.min(t / T.DUR, 1)) + 0.03 * rampa(t, T.finO, 0.9) * (1 - rampa(t, T.REV, 0.5));
	const tPal = d.voz.cita.palabras.map((x) => T.C0 + x);
	// 24 nov 2026: las tres caras se ven desde el primer fotograma (lo que llama la atención en el feed) y vuelven
	// al final para que el bucle enlace sin salto
	const tTarj = [-0.6, -0.6, -0.6]; // ya puestas en el fotograma 0
	const tTarjFin = [T.BUCLE + 0.1, T.BUCLE + 0.18, T.BUCLE + 0.26];
	const tNombre = T.A0 + (d.voz.autor.palabras[0] ?? 0.2) - 0.05;
	const tEtiq = d.voz.autor.etiqueta !== undefined && d.voz.autor.palabras[d.voz.autor.etiqueta] !== undefined ? T.A0 + d.voz.autor.palabras[d.voz.autor.etiqueta] - 0.05 : tNombre + 1.1;
	const letras = d.autor.toUpperCase().split('');
	const tam = tamCita(d.cita);

	return (
		<AbsoluteFill style={{background: '#0b0907'}}>
			<Retrato foto={d.foto} foco={d.foco} t={t} oculto={oculto} zoom={zoom} ancho={W} alto={H} cx={CX} />
			<Textura frame={frame} ancho={W} alto={H} />
			<Barrido t={t} rev={T.REV + 0.1} alto={H} />
			<MarcoTema color={tema.color} t={t} ancho={W} alto={H} />

			{/* Pregunta: primero grande en el centro, luego arriba */}
			<div style={{position: 'absolute', left: CX - 470, width: 940, top: lerp(500, 170, sube), textAlign: 'center', opacity: preguntaVis, transform: `scale(${lerp(1.25, 1, sube)})`, transformOrigin: '50% 0%'}}>
				<Comillas tipo="abre" t={t < T.BUCLE ? t : t - T.BUCLE - 0.2} t0={-0.2} tam={260} estilo={{opacity: 1 - sube, height: lerp(110, 0, sube), overflow: 'visible'}} />
				<div style={{fontFamily: INTER, fontWeight: 800, fontSize: 74, lineHeight: 1.1, color: '#fff', textShadow: '0 4px 24px rgba(0,0,0,0.7)'}}>
					{d.pregunta.split(' ').map((p, i) => {
						const luz = rampa(t, T.G0 + (d.voz.gancho.palabras[i] ?? 0) - 0.04, 0.12) * (1 - rampa(t, T.BUCLE, 0.4));
						return (
							<span key={i} style={{display: 'inline-block', marginRight: 18, opacity: lerp(0.8, 1, luz), color: i === 0 && luz > 0.5 ? AMARILLO : undefined, transform: `scale(${1 + 0.08 * Math.sin(Math.PI * luz)})`}}>
								{p}
							</span>
						);
					})}
				</div>
			</div>

			{/* Frase escrita a pluma: centrada entre la pregunta y las tarjetas; tras revelar, sube */}
			{citaVis > 0.001 && (
				<div style={{position: 'absolute', left: CX - 470, width: 940, top: lerp(290, 130, citaArriba), height: lerp(650, 560, citaArriba), display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: citaVis, transform: `scale(${lerp(1, 0.8, citaArriba)})`}}>
					<CitaPluma cita={d.cita} tiempos={tPal} finVoz={T.O0} t={t} tam={tam} ancho={940} apagar={0} />
				</div>
			)}

			{/* Quiz */}
			{t < T.REV + 0.9 && <Opciones opciones={d.opciones} correcta={d.correcta} entradas={tTarj} t={t} rev={T.REV} salida={tarjetasFuera} cx={CX} top={960} />}
			{t > T.BUCLE && <Opciones opciones={d.opciones} correcta={d.correcta} entradas={tTarjFin} t={t} rev={T.DUR + 99} salida={0} cx={CX} top={960} />}
			<Comenta t={t} t0={T.finO - 0.9} t1={T.REV} cx={CX} top={1480} />

			{/* Ficha del autor */}
			{t > T.REV + 0.6 && fichaVis > 0.001 && (
				<div style={{position: 'absolute', left: CX - 480, width: 960, top: 1010, textAlign: 'center', opacity: fichaVis}}>
					<div style={{height: 3, width: 600 * rampa(t, T.A0, 0.45), margin: '0 auto 16px', background: AMARILLO, borderRadius: 2}} />
					<div style={{fontFamily: INTER, fontWeight: 900, fontSize: letras.length > 22 ? 54 : 66, letterSpacing: 2, color: AMARILLO, whiteSpace: 'nowrap', textShadow: '0 4px 20px rgba(0,0,0,0.8)'}}>
						{letras.map((c, i) => {
							const e = pop(t, tNombre + i * 0.03, 0.3);
							return (
								<span key={i} style={{display: 'inline-block', opacity: Math.min(e * 1.5, 1), transform: `translateY(${(1 - e) * 26}px)`, whiteSpace: 'pre'}}>
									{c}
								</span>
							);
						})}
					</div>
					{d.quien && (
						<div style={{fontFamily: INTER, fontWeight: 600, fontSize: 38, color: '#f4efe4', marginTop: 6, opacity: rampa(t, tNombre + 0.4, 0.4), textShadow: '0 3px 14px rgba(0,0,0,0.8)'}}>
							{d.quien}
						</div>
					)}
					{(d.pais || d.vida) && (
						<div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 26, marginTop: 18}}>
							{d.pais && (
								<div style={{textAlign: 'center'}}>
									<MapaPais pais={d.pais} t={t} t0={tNombre + 0.5} color={tema.color} ancho={250} alto={190} />
									<div style={{fontFamily: INTER, fontWeight: 800, fontSize: 30, color: '#fff', marginTop: 6, opacity: rampa(t, tNombre + 1.1, 0.3), maxWidth: 300}}>
										{d.pais.nombre}
										{d.pais.ciudad && <span style={{fontWeight: 600, color: '#e9e1d0'}}> · {d.pais.ciudad}</span>}
									</div>
								</div>
							)}
							{d.vida && (
								<div style={{opacity: rampa(t, tNombre + 0.9, 0.3)}}>
									<LineaVida {...d.vida} t={t} t0={tNombre + 0.9} color={tema.color} ancho={d.pais ? 560 : 760} />
								</div>
							)}
						</div>
					)}
					<div style={{display: 'flex', justifyContent: 'center', gap: 16, marginTop: 10, height: 56}}>
						{d.etiqueta && <Chapa texto={d.etiqueta} t={t} t0={tEtiq} fondo={AMARILLO} />}
						<Chapa texto={tema.nombre} t={t} t0={tEtiq + 0.35} fondo={tema.color} icono={tema.icono} />
					</div>
					{d.firma && (
						<div style={{height: 96, marginTop: 6, display: 'flex', justifyContent: 'center'}}>
							<Img
								src={staticFile(d.firma)}
								style={{
									height: 96,
									maxWidth: 520,
									objectFit: 'contain',
									filter: 'invert(1) brightness(1.4) contrast(1.6) drop-shadow(0 0 8px rgba(245,197,24,0.35))',
									mixBlendMode: 'screen',
									WebkitMaskImage: `linear-gradient(90deg, #000 ${rampa(t, tEtiq + 0.2, 1.1) * 110 - 10}%, transparent ${rampa(t, tEtiq + 0.2, 1.1) * 110}%)`,
									maskImage: `linear-gradient(90deg, #000 ${rampa(t, tEtiq + 0.2, 1.1) * 110 - 10}%, transparent ${rampa(t, tEtiq + 0.2, 1.1) * 110}%)`,
								}}
							/>
						</div>
					)}
				</div>
			)}

			<Suscribete t={t} s0={T.SUS} fin={T.BUCLE - 0.3} cx={CX} top={170} />

			{/* Comillas que se cierran: sello del canal antes de volver al principio */}
			{t > T.BUCLE - 0.3 && t < T.DUR - 0.2 && (
				<div style={{position: 'absolute', left: CX - 200, width: 400, top: 560, display: 'flex', justifyContent: 'center', opacity: 1 - rampa(t, T.DUR - 0.5, 0.3)}}>
					<Comillas tipo="cierra" t={t} t0={T.BUCLE - 0.3} tam={380} />
				</div>
			)}

			{/* Audio */}
			<Audio src={staticFile(d.musica)} volume={0.18} />
			{(['gancho', 'cita', 'opciones', 'autor'] as const).map((k) => {
				const t0 = {gancho: T.G0, cita: T.C0, opciones: T.O0, autor: T.A0}[k];
				return (
					<Sequence key={k} from={Math.round(t0 * FPS)}>
						<Audio src={staticFile(d.voz[k].archivo)} />
					</Sequence>
				);
			})}
			{[
				{t: 0.02, s: 'pop', v: 0.3},
				...tTarj.map((x) => ({t: x, s: 'pop', v: 0.35})),
				{t: T.finO - 0.9, s: 'subida', v: 0.25},
				{t: T.REV, s: 'campana', v: 0.4},
				{t: T.REV + 0.05, s: 'whoosh', v: 0.35},
				{t: tEtiq, s: 'pop', v: 0.3},
				{t: T.SUS + 0.8, s: 'pop', v: 0.4},
				{t: T.SUS + 0.85, s: 'campana', v: 0.25},
				{t: T.BUCLE - 0.3, s: 'golpe', v: 0.2},
			].map((x, i) => (
				<Sequence key={i} from={Math.max(0, Math.round(x.t * FPS))} durationInFrames={45}>
					<Audio src={staticFile(`sfx/${x.s}.wav`)} volume={x.v} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};
