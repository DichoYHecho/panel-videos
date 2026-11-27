/**
 * Mapa «profesional» para los formatos nuevos (27 nov 2026). Sin datos externos: usa world-atlas 50m (ya
 * instalado) y d3-geo. La cámara entra desde una vista amplia de la región y se acerca al país; se ven la
 * retícula, los países vecinos con su nombre, los mares, el país resaltado con un contorno que se dibuja y
 * brilla, ciudades de referencia, un alfiler con pulso en el lugar del que se habla y la bandera del país.
 */
import React, {useMemo} from 'react';
import {geoCentroid, geoGraticule10, geoMercator, geoPath} from 'd3-geo';
import {feature} from 'topojson-client';
import mundo from 'world-atlas/countries-50m.json';
import {AMARILLO, INTER, lerp, pop, rampa, suave} from './base';

export type Lugar = {nombre: string; lon: number; lat: number};
export type DatosMapa = {
	paisId: string; // código ISO numérico (world-atlas), p. ej. «368» = Irak
	pais: string; // nombre que se muestra
	lugar: Lugar; // el alfiler
	ciudades?: Lugar[]; // referencias (puntos pequeños)
	mares?: Lugar[]; // rótulos de mares en cursiva
	vecinos?: Record<string, string>; // id → nombre en español de los vecinos que se rotulan
	bandera?: string; // código ISO de 2 letras (p. ej. «iq»); ver BANDERAS
	margen?: number; // cuánto contexto alrededor del país (1 = justo)
};

const fc = feature(mundo as any, (mundo as any).objects.countries) as any;

export const MapaPro: React.FC<{m: DatosMapa; t: number; t0: number; tPin?: number; ancho: number; alto: number}> = ({m, t, t0, tPin, ancho, alto}) => {
	const geo = useMemo(() => {
		const propio = fc.features.find((f: any) => String(f.id).padStart(3, '0') === m.paisId.padStart(3, '0'));
		const proy = geoMercator();
		// encuadre: el país con margen alrededor
		proy.fitExtent([[ancho * 0.18, alto * 0.18], [ancho * 0.82, alto * 0.82]], propio);
		const k = m.margen ?? 1;
		proy.scale(proy.scale() / k);
		const c = geoCentroid(propio);
		const [cx, cy] = proy(c) as [number, number];
		proy.translate([proy.translate()[0] + (ancho / 2 - cx), proy.translate()[1] + (alto / 2 - cy)]);
		const camino = geoPath(proy);
		const paises = fc.features.map((f: any) => ({id: String(f.id).padStart(3, '0'), d: camino(f) ?? '', c: proy(geoCentroid(f)) as [number, number]})).filter((p: any) => p.d);
		// zoom inicial: el mundo entero cabe a lo ancho (el mundo mide 2π·escala en Mercator)
		const zMundo = (ancho * 0.98) / (2 * Math.PI * proy.scale());
		return {
			paises,
			propio: camino(propio) ?? '',
			reticula: camino(geoGraticule10()) ?? '',
			px: (l: Lugar) => proy([l.lon, l.lat]) as [number, number],
			zMundo,
			centroMundo: proy([12, 22]) as [number, number], // centro aproximado del mapamundi
		};
	}, [m, ancho, alto]);

	// cámara: mapamundi → zoom hasta el lugar. El zoom se interpola en escala logarítmica (suave de verdad).
	const ZOOM_INI = 0.9; // segundos viendo el mundo entero
	const ZOOM_DUR = 2.0;
	const viaje = suave((t - t0 - ZOOM_INI) / ZOOM_DUR);
	const zoom = Math.exp(lerp(Math.log(geo.zMundo), 0, viaje)) * (1 + 0.04 * rampa(t, t0 + ZOOM_INI + ZOOM_DUR, 4));
	const [lx, ly] = geo.px(m.lugar);
	// el foco va del centro del mundo al lugar (un poco antes que el zoom, para que no se salga de cuadro)
	const vf = suave((t - t0 - ZOOM_INI) / (ZOOM_DUR * 0.7));
	const fx = lerp(geo.centroMundo[0], lerp(ancho / 2, lx, 0.35), vf);
	const fy = lerp(geo.centroMundo[1], lerp(alto / 2, ly, 0.35), vf);
	const camara = `translate(${ancho / 2} ${alto / 2}) scale(${zoom}) translate(${-fx} ${-fy})`;
	const tLlega = t0 + ZOOM_INI + ZOOM_DUR;
	const contorno = rampa(t, tLlega - 0.5, 1.0);
	const relleno = rampa(t, tLlega, 0.6);
	const tp = tPin ?? tLlega + 0.4; // el alfiler cae cuando la voz nombra el lugar
	const ePin = pop(t, tp, 0.45);
	const pulso = ((t - tp - 0.3) % 1.4) / 1.4;
	const eRot = rampa(t, tLlega - 0.3, 0.6);
	const destello = Math.max(0, 1 - Math.abs(t - tLlega + 0.2) / 0.35); // brillo al «aterrizar»
	const s = 1 / zoom; // compensa el zoom para que textos y trazos no cambien de tamaño

	return (
		<div style={{position: 'relative', width: ancho, height: alto, borderRadius: 26, overflow: 'hidden', background: 'radial-gradient(ellipse at 50% 45%, #121820 0%, #0b0e12 70%)', border: '1.5px solid rgba(255,255,255,0.12)'}}>
			<svg width={ancho} height={alto} style={{position: 'absolute', inset: 0}}>
				<defs>
					<linearGradient id="relleno-pais" x1="0" y1="0" x2="1" y2="1">
						<stop offset="0%" stopColor="#f5c518" stopOpacity={0.55} />
						<stop offset="100%" stopColor="#b8860b" stopOpacity={0.35} />
					</linearGradient>
					<filter id="brillo-pais" x="-20%" y="-20%" width="140%" height="140%">
						<feGaussianBlur stdDeviation={6} result="b" />
						<feMerge>
							<feMergeNode in="b" />
							<feMergeNode in="SourceGraphic" />
						</feMerge>
					</filter>
				</defs>
				<g transform={camara}>
					<path d={geo.reticula} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={1.2 * s} />
					{geo.paises.map((p: any) => (
						<path key={p.id} d={p.d} fill={p.id === m.paisId.padStart(3, '0') ? '#1b1d21' : '#17191c'} stroke="rgba(255,255,255,0.20)" strokeWidth={1.1 * s} />
					))}
					<path d={geo.propio} fill="url(#relleno-pais)" fillOpacity={relleno} stroke="none" />
					<path d={geo.propio} fill="none" stroke={AMARILLO} strokeWidth={3.5 * s} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - contorno} filter="url(#brillo-pais)" />
					{/* vecinos y mares */}
					{Object.entries(m.vecinos ?? {}).map(([id, nombre]) => {
						const p = geo.paises.find((q: any) => q.id === id.padStart(3, '0'));
						if (!p) return null;
						return (
							<text key={id} x={p.c[0]} y={p.c[1]} fill="rgba(255,255,255,0.38)" fontFamily={INTER} fontWeight={700} fontSize={26 * s} letterSpacing={3 * s} textAnchor="middle" opacity={eRot} style={{textTransform: 'uppercase'}}>
								{nombre}
							</text>
						);
					})}
					{(m.mares ?? []).map((mar) => {
						const [x, y] = geo.px(mar);
						return (
							<text key={mar.nombre} x={x} y={y} fill="rgba(140,170,210,0.45)" fontFamily={INTER} fontStyle="italic" fontWeight={600} fontSize={24 * s} textAnchor="middle" opacity={eRot}>
								{mar.nombre}
							</text>
						);
					})}
					{/* ciudades de referencia */}
					{(m.ciudades ?? []).map((ci) => {
						const [x, y] = geo.px(ci);
						return (
							<g key={ci.nombre} opacity={relleno}>
								<circle cx={x} cy={y} r={6 * s} fill="#fff" />
								<text x={x + 14 * s} y={y + 8 * s} fill="rgba(255,255,255,0.8)" fontFamily={INTER} fontWeight={700} fontSize={26 * s}>{ci.nombre}</text>
							</g>
						);
					})}
					{/* alfiler */}
					{t > tp + 0.3 && <circle cx={lx} cy={ly} r={(8 + 34 * pulso) * s} fill="none" stroke={AMARILLO} strokeWidth={3 * s} opacity={1 - pulso} />}
					{ePin > 0 && (
						<g transform={`translate(${lx}, ${ly - 50 * s * (1 - ePin)}) scale(${s * 1.5})`} opacity={Math.min(ePin * 1.5, 1)}>
							<path d="M0 0 C -12 -16, -14 -26, -14 -32 A 14 14 0 1 1 14 -32 C 14 -26, 12 -16, 0 0 Z" fill={AMARILLO} stroke="#111" strokeWidth={2} />
							<circle cx={0} cy={-32} r={5} fill="#111" />
						</g>
					)}
					{ePin > 0 && (
						<text x={lx + 30 * s} y={ly - 30 * s} fill="#fff" fontFamily={INTER} fontWeight={900} fontSize={40 * s} opacity={Math.min(ePin * 1.5, 1)} style={{paintOrder: 'stroke'}} stroke="#0b0e12" strokeWidth={8 * s}>
							{m.lugar.nombre}
						</text>
					)}
				</g>
			</svg>
			<div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 50%, rgba(245,197,24,0.35), transparent 60%)', opacity: destello, pointerEvents: 'none'}} />
			{/* rótulo del país con bandera */}
			<div style={{position: 'absolute', left: 30, bottom: 26, display: 'flex', alignItems: 'center', gap: 16, opacity: relleno, transform: `translateY(${20 * (1 - relleno)}px)`}}>
				{m.bandera && BANDERAS[m.bandera] && <div style={{width: 84, height: 56, borderRadius: 6, overflow: 'hidden', boxShadow: '0 4px 16px rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.25)'}}>{React.createElement(BANDERAS[m.bandera])}</div>}
				<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 36, color: '#fff'}}>{m.pais}</span>
			</div>
		</div>
	);
};

/** Bandera de Irak (2008-hoy): rojo, blanco y negro con «Allahu akbar» en verde. */
export const BanderaIrak: React.FC = () => (
	<svg viewBox="0 0 900 600" width="100%" height="100%" preserveAspectRatio="none">
		<rect width={900} height={200} fill="#CE1126" />
		<rect y={200} width={900} height={200} fill="#FFFFFF" />
		<rect y={400} width={900} height={200} fill="#000000" />
		<text x={450} y={340} fill="#007A3D" fontSize={120} fontWeight={700} textAnchor="middle" fontFamily="'Segoe UI', Arial, sans-serif" direction="rtl">الله أكبر</text>
	</svg>
);

/** Banderas dibujadas en SVG (sin descargas). Para producción: un juego completo con licencia libre. */
export const BANDERAS: Record<string, React.FC> = {iq: BanderaIrak};
