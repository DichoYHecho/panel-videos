/**
 * Cierre común de los formatos nuevos (27 nov 2026): cuando la voz termina, tres botones animados piden comentar,
 * dar «me gusta» y seguir. Solo visual (la voz no lo pide) y dentro de la escena final, para que no sea un
 * «pegote». Dura lo que quede de vídeo tras la voz (~2,5 s).
 */
import React from 'react';
import {AMARILLO, INTER, lerp, pop, rampa} from './base';

const Burbuja: React.FC<{tam: number; color: string}> = ({tam, color}) => (
	<svg width={tam} height={tam} viewBox="0 0 48 48">
		<path d="M8 8h32a5 5 0 0 1 5 5v18a5 5 0 0 1-5 5H22l-9 8v-8H8a5 5 0 0 1-5-5V13a5 5 0 0 1 5-5z" fill={color} />
		<circle cx={16} cy={22} r={2.6} fill="#111" />
		<circle cx={24} cy={22} r={2.6} fill="#111" />
		<circle cx={32} cy={22} r={2.6} fill="#111" />
	</svg>
);

const Pulgar: React.FC<{tam: number; lleno: number}> = ({tam, lleno}) => (
	<svg width={tam} height={tam} viewBox="0 0 48 48">
		<path
			d="M15 21l8-14c3 0 5 2 4.5 5L26 19h11a4 4 0 0 1 4 4.6l-2.4 13A4 4 0 0 1 34.7 40H15zM5 21h7v19H5z"
			fill={lleno > 0.5 ? AMARILLO : 'none'}
			stroke={lleno > 0.5 ? AMARILLO : '#fff'}
			strokeWidth={3.2}
			strokeLinejoin="round"
		/>
	</svg>
);

/** `t0`: cuando termina la voz. */
export const Cierre: React.FC<{t: number; t0: number}> = ({t, t0}) => {
	const e = [0, 1, 2].map((i) => pop(t, t0 + i * 0.22, 0.4));
	const tLike = t0 + 0.85;
	const lleno = rampa(t, tLike, 0.08);
	const golpeLike = t > tLike ? Math.max(0, 1 - (t - tLike) / 0.4) : 0;
	const onda = (t - tLike) / 0.6;
	const tSigue = t0 + 1.45;
	const siguiendo = t > tSigue;
	const golpeSigue = t > tSigue ? Math.max(0, 1 - (t - tSigue) / 0.35) : 0;
	const boton = (i: number, icono: React.ReactNode, txt: string, activo = false, golpe = 0) => (
		<div
			key={i}
			style={{
				position: 'relative',
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				gap: 10,
				opacity: Math.min(e[i] * 1.5, 1),
				transform: `translateY(${40 * (1 - e[i])}px) scale(${1 + 0.18 * golpe})`,
			}}
		>
			<div style={{width: 128, height: 128, borderRadius: 64, background: activo ? 'rgba(245,197,24,0.16)' : '#1a1a1a', border: `3px solid ${activo ? AMARILLO : 'rgba(255,255,255,0.22)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{icono}</div>
			<span style={{fontFamily: INTER, fontWeight: 800, fontSize: 32, color: activo ? AMARILLO : '#fff'}}>{txt}</span>
		</div>
	);
	return (
		<div style={{display: 'flex', justifyContent: 'center', gap: 70, marginTop: 50, position: 'relative'}}>
			{boton(0, <Burbuja tam={62} color="#fff" />, 'Comenta')}
			<div style={{position: 'relative'}}>
				{boton(1, <Pulgar tam={62} lleno={lleno} />, 'Me gusta', lleno > 0.5, golpeLike)}
				{onda > 0 && onda < 1 && <div style={{position: 'absolute', left: 64 - lerp(64, 130, onda), top: 64 - lerp(64, 130, onda), width: lerp(128, 260, onda), height: lerp(128, 260, onda), borderRadius: '50%', border: `4px solid ${AMARILLO}`, opacity: 1 - onda}} />}
			</div>
			{boton(
				2,
				<span style={{fontFamily: INTER, fontWeight: 900, fontSize: 60, color: siguiendo ? AMARILLO : '#fff', lineHeight: 1}}>{siguiendo ? '✓' : '+'}</span>,
				siguiendo ? 'Siguiendo' : 'Síguenos',
				siguiendo,
				golpeSigue,
			)}
		</div>
	);
};
