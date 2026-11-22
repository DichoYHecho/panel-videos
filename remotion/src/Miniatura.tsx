/**
 * Miniatura (portada) de un Short quiz, 1080x1920, estilo serio (el del vídeo: archivo, sepia, dorado).
 * La foto entera, enmarcada como un cuadro; la persona, convertida en silueta oscura con un «?» (recorte con
 * rembg), para no destripar la respuesta. Arriba «¿Quién lo dijo?» con tipografía clásica.
 * Se renderiza con `remotion still` (videos/quiz.py).
 */
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {AMARILLO, INTER, PLAYFAIR, PLAYFAIR_IT, Textura} from './base';
import {TEMAS} from './piezas';

export type DatosMiniatura = {
	foto: string; // foto original
	recorte: string; // la misma foto con fondo transparente (solo la persona), mismas medidas
	proporcion: number; // alto / ancho de la foto
	tema: string;
	cabeza?: [number, number]; // centro de la cabeza (0-1) para colocar el «?»
};

const W = 1080;
const H = 1920;

export const Miniatura: React.FC<DatosMiniatura> = ({foto, recorte, proporcion, tema, cabeza = [0.5, 0.33]}) => {
	const t = TEMAS[tema] ?? TEMAS.vida;
	// La foto entera: tan ancha como quepa (con margen), sin recortarla
	const maxAn = 940;
	const maxAl = 1260;
	const an = Math.min(maxAn, maxAl / proporcion);
	const al = an * proporcion;
	const left = (W - an) / 2;
	const top = 400 + (maxAl - al) / 2;
	const capa: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: an, height: al};
	return (
		<AbsoluteFill style={{background: 'radial-gradient(ellipse 90% 80% at 50% 45%, #2a2117 0%, #120d09 75%, #080604 100%)'}}>
			<Textura frame={5} ancho={W} alto={H} degradado="transparent" />

			{/* Pregunta */}
			<div style={{position: 'absolute', top: 150, left: 0, right: 0, textAlign: 'center'}}>
				<div style={{fontFamily: PLAYFAIR, fontWeight: 800, fontSize: 128, lineHeight: 1.05, color: '#fbf6ea', textShadow: '0 6px 30px rgba(0,0,0,0.8)'}}>
					¿Quién lo <span style={{fontFamily: PLAYFAIR_IT, fontStyle: 'italic', color: AMARILLO}}>dijo</span>?
				</div>
			</div>

			{/* El cuadro: foto entera en sepia y, encima, la persona como silueta */}
			<div style={{position: 'absolute', left, top, width: an, height: al, boxShadow: '0 30px 80px rgba(0,0,0,0.8)', outline: `3px solid ${AMARILLO}`, outlineOffset: 14}}>
				<div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
					<Img src={staticFile(foto)} style={{...capa, objectFit: 'cover', filter: 'sepia(0.55) saturate(0.7) brightness(0.8) contrast(1.05)'}} />
					<Img src={staticFile(recorte)} style={{...capa, objectFit: 'cover', filter: 'brightness(0) opacity(0.94) drop-shadow(0 0 2px rgba(245,197,24,0.9)) drop-shadow(0 0 14px rgba(245,197,24,0.35))'}} />
					<AbsoluteFill style={{background: 'radial-gradient(ellipse 75% 70% at 50% 45%, transparent 60%, rgba(0,0,0,0.45) 100%)'}} />
					<div
						style={{
							position: 'absolute',
							left: cabeza[0] * an,
							top: cabeza[1] * al,
							transform: 'translate(-50%, -50%)',
							fontFamily: PLAYFAIR,
							fontWeight: 800,
							fontSize: an * 0.42,
							lineHeight: 1,
							color: AMARILLO,
							textShadow: '0 0 30px rgba(245,197,24,0.45), 0 10px 30px rgba(0,0,0,0.7)',
						}}
					>
						?
					</div>
				</div>
			</div>

			{/* Logo del canal */}
			<div style={{position: 'absolute', bottom: 56, left: 0, right: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 22}}>
				<Img src={staticFile('logo.jpg')} style={{width: 118, height: 118, borderRadius: 59, border: `3px solid ${AMARILLO}`, boxShadow: '0 8px 24px rgba(0,0,0,0.7)'}} />
				<div style={{fontFamily: PLAYFAIR, fontWeight: 800, fontSize: 56, color: '#fbf6ea'}}>Dicho y Hecho</div>
			</div>
		</AbsoluteFill>
	);
};
