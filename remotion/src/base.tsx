/**
 * Piezas comunes de Dicho y Hecho: utilidades de animación, retrato con profundidad, textura de archivo,
 * barrido de luz y gancho de suscripción. Las usan el Short (Quiz.tsx) y el vídeo largo semanal.
 */
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {loadFont as cargarInter} from '@remotion/google-fonts/Inter';
import {loadFont as cargarPlayfair} from '@remotion/google-fonts/PlayfairDisplay';

export const INTER = cargarInter('normal', {weights: ['500', '600', '700', '800', '900'], subsets: ['latin', 'latin-ext']}).fontFamily;
export const PLAYFAIR = cargarPlayfair('normal', {weights: ['700', '800'], subsets: ['latin', 'latin-ext']}).fontFamily;
export const PLAYFAIR_IT = cargarPlayfair('italic', {weights: ['600', '700'], subsets: ['latin', 'latin-ext']}).fontFamily;

export const FPS = 30;
export const AMARILLO = '#F5C518';
export const VERDE = '#4CC38A';
export const ROJO = '#E5484D';

// ---------------------------------------------------------------- utilidades
export const suave = (x: number) => {
	const c = Math.min(Math.max(x, 0), 1);
	return c * c * (3 - 2 * c);
};
export const rampa = (t: number, a: number, d: number) => suave((t - a) / d);
/** Sale de 0 a 1 con un pequeño rebote (0 → ~1.06 → 1). */
export const pop = (t: number, a: number, d: number) => {
	const x = Math.min(Math.max((t - a) / d, 0), 1);
	return x <= 0 ? 0 : 1 - (1 - x) ** 3 + 0.08 * Math.sin(Math.PI * x) * (1 - x);
};
export const lerp = (a: number, b: number, f: number) => a + (b - a) * f;
export const azar = (n: number) => {
	const x = Math.sin(n * 12.9898 + 78.233) * 43758.5453;
	return x - Math.floor(x);
};
export const partes = (txt: string) => txt.split(' ').map((p) => ({txt: p.replace(/\*/g, ''), clave: p.includes('*')}));

// ---------------------------------------------------------------- retrato con profundidad
/**
 * Retrato a pantalla completa. `oculto` 1 = muy desenfocado y oscuro; 0 = nítido, con la cara (máscara
 * elíptica) más nítida que el fondo. `origen` y `escala` encuadran la cara.
 */
export const Retrato: React.FC<{
	foto: string;
	foco: [number, number];
	t: number;
	oculto: number;
	zoom: number;
	ancho: number;
	alto: number;
	cx: number;
	escala?: number;
	origenY?: number;
	caraY?: number;
}> = ({foto, foco, t, oculto, zoom, ancho, alto, cx, escala = 1.3, origenY = 1100, caraY = 36}) => {
	const parpadeo = 1 + (azar(Math.floor(t * FPS)) - 0.5) * 0.025;
	const brillo = lerp(0.85, 0.5, oculto) * parpadeo;
	const comun: React.CSSProperties = {
		position: 'absolute',
		inset: 0,
		width: '100%',
		height: '100%',
		objectFit: 'cover',
		objectPosition: `${foco[0] * 100}% ${foco[1] * 100}%`,
	};
	const mascara = `radial-gradient(ellipse 34% 26% at ${(cx / ancho) * 100}% ${caraY}%, #000 55%, transparent 100%)`;
	return (
		<AbsoluteFill style={{transform: `scale(${escala * zoom})`, transformOrigin: `${cx}px ${origenY}px`}}>
			<Img
				src={staticFile(foto)}
				style={{...comun, filter: `blur(${lerp(5, 34, oculto)}px) brightness(${brillo * 0.85}) saturate(${lerp(0.9, 0.3, oculto)}) sepia(0.25)`}}
			/>
			<Img
				src={staticFile(foto)}
				style={{
					...comun,
					filter: `blur(${lerp(0, 34, oculto)}px) brightness(${brillo}) saturate(${lerp(0.95, 0.3, oculto)}) sepia(0.2) contrast(1.06)`,
					WebkitMaskImage: mascara,
					maskImage: mascara,
				}}
			/>
			{/* alto se usa para que el componente sirva igual en vertical y en horizontal */}
			<div style={{position: 'absolute', width: ancho, height: alto, pointerEvents: 'none'}} />
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- textura de archivo
export const Textura: React.FC<{frame: number; ancho: number; alto: number; degradado?: string}> = ({frame, ancho, alto, degradado}) => {
	const motas = Array.from({length: 7}, (_, i) => {
		const k = Math.floor(frame / 3) * 7 + i;
		return {x: azar(k) * ancho, y: azar(k + 0.5) * alto, r: 1 + azar(k + 0.7) * 2.5, a: 0.15 + azar(k + 0.9) * 0.35};
	});
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<AbsoluteFill
				style={{
					background:
						degradado ??
						'linear-gradient(180deg, rgba(8,6,4,0.8) 0%, rgba(8,6,4,0.2) 28%, rgba(8,6,4,0.1) 42%, rgba(8,6,4,0.72) 58%, rgba(8,6,4,0.94) 100%)',
				}}
			/>
			<AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 70% at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
			<svg width={ancho} height={alto} style={{position: 'absolute', inset: 0, mixBlendMode: 'overlay', opacity: 0.22}}>
				<filter id={`grano${frame}`}>
					<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={frame % 24} stitchTiles="stitch" />
					<feColorMatrix type="saturate" values="0" />
				</filter>
				<rect width="100%" height="100%" filter={`url(#grano${frame})`} />
			</svg>
			<svg width={ancho} height={alto} style={{position: 'absolute', inset: 0}}>
				{motas.map((m, i) => (
					<circle key={i} cx={m.x} cy={m.y} r={m.r} fill="#e9dfc8" opacity={m.a} />
				))}
			</svg>
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- barrido de luz
export const Barrido: React.FC<{t: number; rev: number; alto: number}> = ({t, rev, alto}) => {
	const p = (t - rev + 0.1) / 0.65;
	if (p < 0 || p > 1) return null;
	return (
		<AbsoluteFill style={{mixBlendMode: 'screen', pointerEvents: 'none'}}>
			<div
				style={{
					position: 'absolute',
					top: -400,
					left: lerp(-900, 1900, suave(p)),
					width: 420,
					height: alto + 800,
					transform: 'rotate(18deg)',
					background: 'linear-gradient(90deg, transparent, rgba(255,236,190,0.55), transparent)',
					filter: 'blur(20px)',
				}}
			/>
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- gancho de suscripción
export const SUS_T = {titulo: 0, boton: 0.15, cursor: 0.3, clic: 0.8, sub: 1.0};

const Campana: React.FC<{color: string; giro: number}> = ({color, giro}) => (
	<svg width={46} height={46} viewBox="0 0 24 24" style={{transform: `rotate(${giro}deg)`, transformOrigin: '50% 10%'}}>
		<path d="M12 2.5c-.8 0-1.5.7-1.5 1.5v.6C7.9 5.3 6 7.6 6 10.4V15l-1.8 2.2c-.3.4 0 .9.5.9h14.6c.5 0 .8-.5.5-.9L18 15v-4.6c0-2.8-1.9-5.1-4.5-5.8V4c0-.8-.7-1.5-1.5-1.5z" fill={color} />
		<path d="M9.8 19.4a2.3 2.3 0 0 0 4.4 0z" fill={color} />
	</svg>
);

const Cursor: React.FC = () => (
	<svg width={74} height={74} viewBox="0 0 24 24">
		<path
			d="M9 11.2V4.6a1.6 1.6 0 0 1 3.2 0v5.2l.4-.1a1.6 1.6 0 0 1 2 1l.1.3a1.6 1.6 0 0 1 2.3.9 1.6 1.6 0 0 1 2.2 1.4v3.4c0 3.3-2.4 5.8-5.6 5.8h-1.1c-1.8 0-3.4-.8-4.5-2.2L5 15.9a1.6 1.6 0 0 1 2.4-2.1L9 15.3z"
			fill="#fff"
			stroke="#111"
			strokeWidth={1.2}
			strokeLinejoin="round"
		/>
	</svg>
);

/** «¿La acertaste?» + botón «Suscríbete» que un cursor pulsa → «Suscrito ✓» con campana. */
export const Suscribete: React.FC<{t: number; s0: number; fin: number; cx: number; top: number; titulo?: boolean}> = ({t, s0, fin, cx, top, titulo = true}) => {
	const salida = 1 - rampa(t, fin - 0.3, 0.3);
	if (t < s0 || salida <= 0.001) return null;
	const r = t - s0;
	const eTit = pop(r, SUS_T.titulo, 0.35);
	const eBot = pop(r, SUS_T.boton, 0.4);
	const pulsado = r >= SUS_T.clic;
	const hundir = pulsado
		? 1 - 0.1 * Math.max(0, 1 - (r - SUS_T.clic) / 0.1) + 0.06 * Math.sin(Math.PI * Math.min(Math.max((r - SUS_T.clic - 0.1) / 0.22, 0), 1))
		: 1;
	const ida = suave((r - SUS_T.cursor) / 0.45);
	const vuelta = rampa(r, SUS_T.clic + 0.35, 0.35);
	const curX = lerp(cx + 370, cx + 120, ida) + 260 * vuelta;
	const curY = lerp(top + 560, top + 170, ida) + 300 * vuelta;
	const cOp = Math.min(rampa(r, SUS_T.cursor, 0.12), 1 - vuelta);
	const onda = rampa(r, SUS_T.clic, 0.45);
	const giro = pulsado ? 22 * Math.sin((r - SUS_T.clic) * 22) * Math.exp(-(r - SUS_T.clic) * 3.2) : 0;
	const eSub = pop(r, SUS_T.sub, 0.4);
	return (
		<AbsoluteFill style={{opacity: salida, pointerEvents: 'none'}}>
			<div style={{position: 'absolute', left: cx - 470, width: 940, top, textAlign: 'center'}}>
				{titulo && (
					<div style={{fontFamily: INTER, fontWeight: 800, fontSize: 62, color: '#fff', textShadow: '0 4px 24px rgba(0,0,0,0.7)', opacity: Math.min(eTit * 1.4, 1), transform: `translateY(${(1 - eTit) * 20}px)`}}>
						¿La <span style={{color: AMARILLO}}>acertaste</span>?
					</div>
				)}
				<div style={{height: 120, marginTop: 20, display: 'flex', justifyContent: 'center', position: 'relative'}}>
					{onda > 0 && onda < 1 && (
						<div style={{position: 'absolute', left: '50%', top: '50%', width: 500, height: 120, marginLeft: -250, marginTop: -60, borderRadius: 60, border: `${5 * (1 - onda)}px solid ${AMARILLO}`, opacity: 1 - onda, transform: `scale(${1 + 0.35 * onda})`}} />
					)}
					<div
						style={{
							display: 'flex',
							alignItems: 'center',
							gap: 18,
							height: 120,
							padding: '0 48px 0 38px',
							borderRadius: 60,
							background: pulsado ? 'rgba(40,36,30,0.92)' : '#E5262B',
							border: pulsado ? `2px solid ${AMARILLO}` : '2px solid transparent',
							boxShadow: pulsado ? '0 10px 40px rgba(0,0,0,0.5)' : '0 10px 40px rgba(229,38,43,0.45)',
							fontFamily: INTER,
							fontWeight: 900,
							fontSize: 48,
							color: '#fff',
							opacity: Math.min(eBot * 1.4, 1),
							transform: `scale(${eBot * hundir})`,
						}}
					>
						<Campana color={pulsado ? AMARILLO : '#fff'} giro={giro} />
						{pulsado ? 'SUSCRITO' : 'SUSCRÍBETE'}
						{pulsado && <span style={{color: AMARILLO, fontSize: 46, transform: `scale(${pop(r, SUS_T.clic, 0.3)})`}}>✓</span>}
					</div>
				</div>
				<div style={{marginTop: 20, fontFamily: INTER, fontWeight: 700, fontSize: 40, color: '#f1ece2', textShadow: '0 4px 24px rgba(0,0,0,0.8)', opacity: Math.min(eSub * 1.4, 1), transform: `translateY(${(1 - eSub) * 16}px)`}}>
					Mañana, otra. <span style={{color: AMARILLO}}>¿La adivinarás?</span>
				</div>
			</div>
			{cOp > 0.01 && (
				<div style={{position: 'absolute', left: curX - 22, top: curY - 6, opacity: cOp, transform: `scale(${pulsado && r < SUS_T.clic + 0.12 ? 0.82 : 1})`, transformOrigin: '30% 10%', filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.5))'}}>
					<Cursor />
				</div>
			)}
		</AbsoluteFill>
	);
};
