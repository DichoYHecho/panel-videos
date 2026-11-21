/**
 * Piezas propias de Dicho y Hecho: comillas de marca, frase escrita a pluma, tarjetas del quiz,
 * mapa del país, línea de vida, chapas y marco de color por tema.
 */
import React, {useMemo} from 'react';
import {Img, staticFile} from 'remotion';
import {geoMercator, geoPath} from 'd3-geo';
import {feature} from 'topojson-client';
import mundo from 'world-atlas/countries-50m.json';
import {AMARILLO, INTER, PLAYFAIR, PLAYFAIR_IT, ROJO, VERDE, lerp, partes, pop, rampa, suave} from './base';

// ---------------------------------------------------------------- comillas de marca
/** Comillas del logo: «“» se abre al empezar, «”» se cierra al final (sello). */
export const Comillas: React.FC<{tipo: 'abre' | 'cierra'; t: number; t0: number; tam: number; color?: string; estilo?: React.CSSProperties}> = ({tipo, t, t0, tam, color = AMARILLO, estilo}) => {
	const e = pop(t, t0, 0.45);
	const giro = tipo === 'abre' ? -25 * (1 - e) : 25 * (1 - e);
	return (
		<div
			style={{
				fontFamily: PLAYFAIR,
				fontWeight: 800,
				fontSize: tam,
				lineHeight: 0.62,
				height: tam * 0.42,
				color,
				opacity: Math.min(e * 1.5, 1),
				transform: `scale(${0.4 + 0.6 * e}) rotate(${giro}deg)`,
				textShadow: `0 0 ${30 * (1 - Math.min(Math.abs(t - t0 - 0.2) / 0.5, 1))}px rgba(245,197,24,0.8)`,
				...estilo,
			}}
		>
			{tipo === 'abre' ? '“' : '”'}
		</div>
	);
};

// ---------------------------------------------------------------- frase escrita a pluma
const Pluma: React.FC<{color: string}> = ({color}) => (
	<svg width={70} height={70} viewBox="0 0 64 64" style={{position: 'absolute', right: -40, bottom: 4, transform: 'rotate(8deg)', filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.6))'}}>
		<path d="M60 4C44 6 30 16 22 30L16 44l4 4 14-6C48 34 58 20 60 4z" fill="#f4ecdc" stroke="#3b2f22" strokeWidth={1.5} />
		<path d="M60 4L20 48" stroke="#3b2f22" strokeWidth={1.2} />
		<path d="M16 44l-6 14 10-8z" fill={color} />
	</svg>
);

/**
 * La frase se «escribe» palabra a palabra al ritmo de la voz: cada palabra se descubre de izquierda a
 * derecha con una pluma en la punta. Las *palabras clave* quedan en amarillo con subrayado de tinta.
 */
export const CitaPluma: React.FC<{
	cita: string;
	tiempos: number[]; // segundo (absoluto) en que la voz dice cada palabra
	finVoz: number;
	t: number;
	tam: number;
	ancho: number;
	apagar: number;
}> = ({cita, tiempos, finVoz, t, tam, ancho, apagar}) => {
	const ps = partes(cita);
	return (
		<div style={{fontFamily: PLAYFAIR_IT, fontWeight: 700, fontStyle: 'italic', fontSize: tam, lineHeight: 1.16, color: '#fbf6ea', width: ancho, textAlign: 'center'}}>
			{ps.map((p, i) => {
				const a = tiempos[i] - 0.06;
				const b = Math.max(a + 0.18, Math.min(tiempos[i + 1] ?? finVoz, a + 0.55));
				const prog = suave((t - a) / (b - a)) * (1 - apagar);
				const activa = prog > 0.01 && prog < 0.99;
				return (
					<span key={i} style={{display: 'inline-block', margin: '0 12px', position: 'relative'}}>
						<span
							style={{
								display: 'inline-block',
								color: p.clave ? AMARILLO : undefined,
								clipPath: `inset(-20% ${100 - prog * 100}% -30% -5%)`,
								textShadow: '0 4px 30px rgba(0,0,0,0.8)',
							}}
						>
							{p.txt}
						</span>
						{p.clave && prog > 0.6 && (
							<svg viewBox="0 0 100 12" preserveAspectRatio="none" style={{position: 'absolute', left: -4, bottom: -4, height: 14, width: 'calc(100% + 8px)'}}>
								<path d="M2 8 C 20 3, 40 10, 60 6 S 90 4, 98 7" fill="none" stroke={AMARILLO} strokeWidth={4} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - suave((prog - 0.6) / 0.4)} />
							</svg>
						)}
						{activa && (
							<span style={{position: 'absolute', top: 0, bottom: 0, left: `${prog * 100}%`, width: 0}}>
								<Pluma color={p.clave ? AMARILLO : '#2b2116'} />
							</span>
						)}
					</span>
				);
			})}
		</div>
	);
};

// ---------------------------------------------------------------- tarjetas del quiz
/** `zoom` amplía la foto alrededor del foco (la cara): así no se ven rótulos pintados con el nombre. */
export type Opcion = {nombre: string; foto: string; foco: [number, number]; zoom?: number};

/**
 * Tres tarjetas (A, B, C) con retrato y nombre. Cada una entra cuando la voz la nombra. En la revelación
 * la correcta se marca en verde y las otras se apagan con una cruz roja.
 */
export const Opciones: React.FC<{
	opciones: Opcion[];
	correcta: number;
	entradas: number[]; // segundo (absoluto) en que entra cada tarjeta
	t: number;
	rev: number;
	salida: number; // 0-1: las tarjetas se van
	cx: number;
	top: number;
}> = ({opciones, correcta, entradas, t, rev, salida, cx, top}) => {
	const AN = 296;
	const AL = 380;
	const HUECO = 22;
	const total = AN * 3 + HUECO * 2;
	const marca = rampa(t, rev, 0.3);
	return (
		<div style={{position: 'absolute', left: cx - total / 2, top, width: total, height: AL + 120, display: 'flex', gap: HUECO, opacity: 1 - salida}}>
			{opciones.map((o, i) => {
				const e = pop(t, entradas[i], 0.45);
				const ok = i === correcta;
				const apaga = ok ? 0 : marca;
				return (
					<div key={i} style={{width: AN, opacity: Math.min(e * 1.4, 1) * (1 - 0.55 * apaga), transform: `translateY(${(1 - e) * 80}px) scale(${(0.85 + 0.15 * e) * (ok ? 1 + 0.06 * marca : 1 - 0.06 * apaga)})`}}>
						<div
							style={{
								position: 'relative',
								width: AN,
								height: AL,
								borderRadius: 26,
								overflow: 'hidden',
								border: `5px solid ${ok && marca > 0 ? VERDE : 'rgba(255,255,255,0.85)'}`,
								boxShadow: ok && marca > 0 ? `0 0 ${50 * marca}px rgba(76,195,138,0.8)` : '0 14px 40px rgba(0,0,0,0.55)',
							}}
						>
							<Img
								src={staticFile(o.foto)}
								style={{
									width: '100%',
									height: '100%',
									objectFit: 'cover',
									objectPosition: `${o.foco[0] * 100}% ${o.foco[1] * 100}%`,
									transform: `scale(${o.zoom ?? 1})`,
									transformOrigin: `${o.foco[0] * 100}% ${o.foco[1] * 100}%`,
									filter: `grayscale(${apaga}) sepia(0.2) brightness(${1 - 0.3 * apaga})`,
								}}
							/>
							<div style={{position: 'absolute', left: 14, top: 14, width: 66, height: 66, borderRadius: 33, background: AMARILLO, color: '#111', fontFamily: INTER, fontWeight: 900, fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.5)'}}>
								{'ABC'[i]}
							</div>
							{marca > 0 && (
								<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
									<div style={{width: 130, height: 130, borderRadius: 65, background: ok ? VERDE : ROJO, color: '#fff', fontFamily: INTER, fontWeight: 900, fontSize: 84, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${pop(t, rev + (ok ? 0.05 : 0.15), 0.4)})`, boxShadow: '0 8px 30px rgba(0,0,0,0.5)'}}>
										{ok ? '✓' : '✕'}
									</div>
								</div>
							)}
						</div>
						<div style={{marginTop: 14, fontFamily: INTER, fontWeight: 800, fontSize: 36, lineHeight: 1.1, color: ok && marca > 0 ? VERDE : '#fff', textAlign: 'center', textShadow: '0 3px 14px rgba(0,0,0,0.8)'}}>{o.nombre}</div>
					</div>
				);
			})}
		</div>
	);
};

/** «Comenta: ¿A, B o C?» con una cuenta atrás de tres puntos. */
export const Comenta: React.FC<{t: number; t0: number; t1: number; cx: number; top: number}> = ({t, t0, t1, cx, top}) => {
	const e = pop(t, t0, 0.4) * (1 - rampa(t, t1 - 0.2, 0.2));
	if (e <= 0.01) return null;
	const paso = (t1 - t0) / 3;
	return (
		<div style={{position: 'absolute', left: cx - 400, width: 800, top, display: 'flex', justifyContent: 'center', opacity: Math.min(e * 1.4, 1), transform: `scale(${0.8 + 0.2 * e})`}}>
			<div style={{display: 'flex', alignItems: 'center', gap: 18, padding: '16px 34px', borderRadius: 50, background: 'rgba(0,0,0,0.6)', border: `3px solid ${AMARILLO}`, fontFamily: INTER, fontWeight: 800, fontSize: 46, color: '#fff'}}>
				💬 Comenta: <span style={{color: AMARILLO}}>¿A, B o C?</span>
				{[0, 1, 2].map((k) => {
					const on = t >= t0 + paso * (k + 0.2);
					return <span key={k} style={{width: 16, height: 16, borderRadius: 8, background: on ? AMARILLO : 'rgba(255,255,255,0.25)', transform: `scale(${on ? 1 + 0.4 * (1 - rampa(t, t0 + paso * (k + 0.2), 0.25)) : 1})`}} />;
				})}
			</div>
		</div>
	);
};

// ---------------------------------------------------------------- mapa del país
/** id = código ISO 3166-1 numérico (Wikidata P299), como en Natural Earth / world-atlas. */
export type Pais = {nombre: string; id: string; ciudad: string; lon: number; lat: number};

/**
 * Encuadre: los trozos del país cercanos al lugar de nacimiento (así no salen Canarias, Alaska ni territorios
 * de ultramar), con un margen; si el país no está en el mapa, una ventana alrededor del lugar.
 */
const encuadre = (fc: any, pais: Pais): [number, number][] => {
	const f = fc.features.find((x: any) => String(x.id).padStart(3, '0') === pais.id.padStart(3, '0'));
	const puntos: [number, number][] = [];
	if (f) {
		const polis = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
		for (const p of polis) {
			const anillo: [number, number][] = p[0];
			const cerca = anillo.some(([lo, la]) => Math.abs(lo - pais.lon) < 14 && Math.abs(la - pais.lat) < 12);
			if (cerca) puntos.push(...anillo);
		}
	}
	if (puntos.length < 3) return [[pais.lon - 6, pais.lat - 4], [pais.lon + 6, pais.lat + 4]];
	let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
	for (const [lo, la] of puntos) {
		x0 = Math.min(x0, lo); x1 = Math.max(x1, lo); y0 = Math.min(y0, la); y1 = Math.max(y1, la);
	}
	const mx = Math.max((x1 - x0) * 0.12, 1.2);
	const my = Math.max((y1 - y0) * 0.12, 1);
	return [[x0 - mx, y0 - my], [x1 + mx, y1 + my]];
};

/** Mini mapa: los países vecinos en gris, el del autor se rellena con el color del tema y cae un alfiler. */
export const MapaPais: React.FC<{pais: Pais; t: number; t0: number; color: string; ancho: number; alto: number}> = ({pais, t, t0, color, ancho, alto}) => {
	const geo = useMemo(() => {
		const fc = feature(mundo as any, (mundo as any).objects.countries) as any;
		const proy = geoMercator().fitExtent(
			[
				[10, 10],
				[ancho - 10, alto - 10],
			],
			{type: 'MultiPoint', coordinates: encuadre(fc, pais)} as any,
		);
		const camino = geoPath(proy);
		const vecinos: string[] = [];
		let propio = '';
		for (const f of fc.features) {
			const d = camino(f) ?? '';
			if (!d) continue;
			if (String(f.id).padStart(3, '0') === pais.id.padStart(3, '0')) propio = d;
			else vecinos.push(d);
		}
		return {vecinos, propio, punto: proy([pais.lon, pais.lat]) as [number, number]};
	}, [pais, ancho, alto]);
	const eMapa = rampa(t, t0, 0.5);
	const eRelleno = rampa(t, t0 + 0.25, 0.5);
	const caida = pop(t, t0 + 0.6, 0.45);
	const pulso = ((t - t0 - 1.0) % 1.2) / 1.2;
	return (
		<svg width={ancho} height={alto} style={{overflow: 'hidden', borderRadius: 18, background: 'rgba(10,8,6,0.55)', border: '1.5px solid rgba(255,255,255,0.18)', opacity: eMapa}}>
			{geo.vecinos.map((d, i) => (
				<path key={i} d={d} fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.22)" strokeWidth={0.8} />
			))}
			<path d={geo.propio} fill={color} fillOpacity={0.75 * eRelleno} stroke={color} strokeWidth={2} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - eMapa} />
			{t > t0 + 1.0 && <circle cx={geo.punto[0]} cy={geo.punto[1]} r={6 + 22 * pulso} fill="none" stroke={AMARILLO} strokeWidth={3} opacity={1 - pulso} />}
			{caida > 0 && (
				<g transform={`translate(${geo.punto[0]}, ${geo.punto[1] - 40 * (1 - caida)})`} opacity={Math.min(caida * 1.5, 1)}>
					<path d="M0 0 C -12 -16, -14 -26, -14 -32 A 14 14 0 1 1 14 -32 C 14 -26, 12 -16, 0 0 Z" fill={AMARILLO} stroke="#111" strokeWidth={2} />
					<circle cx={0} cy={-32} r={5} fill="#111" />
				</g>
			)}
		</svg>
	);
};

// ---------------------------------------------------------------- línea de vida
/** «-470» → «470 a. C.»; si la vida empieza antes de Cristo, los años positivos llevan «d. C.». */
export const anio = (a: number, conEra = false) => (a < 0 ? `${-a} a. C.` : conEra ? `${a} d. C.` : String(a));

/** Barra de nacimiento a muerte; si se sabe cuándo es la frase, ese tramo (o ese año) en el color del tema. */
export const LineaVida: React.FC<{nace: number; muere: number; tramo?: [number, number]; rotulo?: string; t: number; t0: number; color: string; ancho: number}> = ({nace, muere, tramo, rotulo, t, t0, color, ancho}) => {
	const x = (a: number) => 20 + ((a - nace) / Math.max(muere - nace, 1)) * (ancho - 40);
	const crece = rampa(t, t0, 0.7);
	const eTramo = tramo ? rampa(t, t0 + 0.55, 0.45) : 0;
	const xa = tramo ? x(Math.max(tramo[0], nace)) : 0;
	const xb = tramo ? Math.max(x(Math.min(tramo[1], muere)), xa + 14) : 0; // un solo año: una marca de 14 px
	return (
		<svg width={ancho} height={160} style={{overflow: 'visible'}}>
			<line x1={20} y1={70} x2={lerp(20, ancho - 20, crece)} y2={70} stroke="rgba(255,255,255,0.75)" strokeWidth={5} strokeLinecap="round" />
			{tramo && <rect x={xa} y={58} width={(xb - xa) * eTramo} height={24} rx={8} fill={color} />}
			{[nace, muere].map((a, i) => (
				<g key={i} opacity={rampa(t, t0 + i * 0.5, 0.3)}>
					<circle cx={x(a)} cy={70} r={11} fill={i ? '#fff' : AMARILLO} stroke="#111" strokeWidth={2} />
					<text x={x(a)} y={36} fill="#fff" fontFamily={INTER} fontWeight={800} fontSize={nace < 0 ? 28 : 34} textAnchor="middle">{anio(a, nace < 0)}</text>
					<text x={x(a)} y={114} fill="rgba(255,255,255,0.8)" fontFamily={INTER} fontWeight={700} fontSize={27} textAnchor="middle">{i ? 'muere' : 'nace'}</text>
				</g>
			))}
			{rotulo && <text x={ancho / 2} y={150} fill={color} fontFamily={INTER} fontWeight={800} fontSize={29} textAnchor="middle" opacity={eTramo}>{rotulo}</text>}
		</svg>
	);
};

// ---------------------------------------------------------------- chapas y marco por tema
export const Chapa: React.FC<{texto: string; t: number; t0: number; fondo: string; color?: string; icono?: string}> = ({texto, t, t0, fondo, color = '#111', icono}) => {
	const e = pop(t, t0, 0.4);
	return (
		<span
			style={{
				display: 'inline-flex',
				alignItems: 'center',
				gap: 10,
				fontFamily: INTER,
				fontWeight: 800,
				fontSize: 28,
				letterSpacing: 2.5,
				textTransform: 'uppercase',
				whiteSpace: 'nowrap',
				color,
				background: fondo,
				padding: '10px 20px 9px',
				borderRadius: 10,
				opacity: Math.min(e * 1.4, 1),
				transform: `scale(${e}) rotate(${-2 * e}deg)`,
				boxShadow: `0 0 ${30 * Math.max(0, 1 - Math.abs(t - t0 - 0.15) / 0.5)}px ${fondo}`,
			}}
		>
			{icono && <span style={{fontSize: 30}}>{icono}</span>}
			{texto}
		</span>
	);
};

/** Cuatro esquinas en el color del tema que se dibujan al empezar: cada tema tiene su color. */
export const MarcoTema: React.FC<{color: string; t: number; ancho: number; alto: number; margen?: number}> = ({color, t, ancho, alto, margen = 34}) => {
	const e = rampa(t, 0, 0.6);
	const L = 110 * e;
	const m = margen;
	const s = {stroke: color, strokeWidth: 7, strokeLinecap: 'round' as const, fill: 'none', opacity: 0.9};
	return (
		<svg width={ancho} height={alto} style={{position: 'absolute', inset: 0, pointerEvents: 'none', filter: `drop-shadow(0 0 10px ${color})`}}>
			<path d={`M${m} ${m + L} V${m} H${m + L}`} {...s} />
			<path d={`M${ancho - m - L} ${m} H${ancho - m} V${m + L}`} {...s} />
			<path d={`M${m} ${alto - m - L} V${alto - m} H${m + L}`} {...s} />
			<path d={`M${ancho - m - L} ${alto - m} H${ancho - m} V${alto - m - L}`} {...s} />
		</svg>
	);
};

/** Colores por tema (se eligen en la publicación): cada serie temática se reconoce por su color. */
export const TEMAS: Record<string, {nombre: string; color: string; icono: string}> = {
	fe: {nombre: 'Fe y esperanza', color: '#D9B45A', icono: '🕊️'},
	vida: {nombre: 'La vida y el tiempo', color: '#E08A3C', icono: '⏳'},
	amor: {nombre: 'Amor', color: '#D0506A', icono: '❤️'},
	ciencia: {nombre: 'Ciencia y razón', color: '#4A9BD8', icono: '🔭'},
	coraje: {nombre: 'Coraje y libertad', color: '#4FB07A', icono: '🗝️'},
	sociedad: {nombre: 'Sociedad y sátira', color: '#A77BE0', icono: '🎭'},
};
