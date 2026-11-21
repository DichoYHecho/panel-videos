/**
 * Datos de un Short «¿Quién escribió esto?». Los prepara videos/quiz.py a partir de Airtable (Cita, Autor,
 * Fuente, foto), del banco de citas (las dos opciones falsas) y de Wikidata (país, lugar, fechas, firma).
 * Los tiempos de la voz son segundos DENTRO de cada trozo de audio (videos/tts.py, con Whisper).
 * Rutas de archivos: relativas a remotion/public.
 */
import type {Opcion, Pais} from './piezas';

export type DatosQuiz = {
	pregunta: string;
	cita: string; // palabras separadas por espacios; *palabra* = clave (amarillo)
	opciones: Opcion[]; // 3; las falsas son autores reales del banco de citas
	correcta: number;
	autor: string;
	quien: string; // «Quién era» (Airtable)
	etiqueta?: string | null; // dónde lo dijo o escribió (chapa)
	tema: string; // clave de TEMAS
	pais?: Pais | null; // sin país, no hay mapa
	vida?: {nace: number; muere: number; tramo?: [number, number]; rotulo?: string} | null; // años; negativos = a. C.
	foto: string;
	foco: [number, number];
	firma?: string | null;
	musica: string;
	voz: {
		gancho: {archivo: string; dur: number; palabras: number[]};
		cita: {archivo: string; dur: number; palabras: number[]};
		opciones: {archivo: string; dur: number; palabras: number[]; tarjetas: number[]};
		autor: {archivo: string; dur: number; palabras: number[]; etiqueta?: number};
	};
};

export const EJEMPLO: DatosQuiz = {
	pregunta: '¿Quién escribió esto?',
	cita: 'Poderoso caballero es *don* *Dinero.*',
	opciones: [
		{nombre: 'Lope de Vega', foto: 'ejemplo/lope.jpg', foco: [0.42, 0.3], zoom: 1.5},
		{nombre: 'Francisco de Quevedo', foto: 'ejemplo/quevedo.jpg', foco: [0.43, 0.47], zoom: 1.9},
		{nombre: 'Calderón de la Barca', foto: 'ejemplo/calderon.jpg', foco: [0.45, 0.35], zoom: 1.5},
	],
	correcta: 1,
	autor: 'Francisco de Quevedo',
	quien: 'Escritor del Siglo de Oro',
	etiqueta: 'Letrilla satírica',
	tema: 'sociedad',
	pais: {nombre: 'España', id: '724', ciudad: 'Madrid', lon: -3.7033, lat: 40.4169},
	vida: {nace: 1580, muere: 1645},
	foto: 'ejemplo/quevedo.jpg',
	foco: [0.47, 0.42],
	musica: 'ejemplo/musica.wav',
	voz: {
		gancho: {archivo: 'ejemplo/gancho.wav', dur: 1.56, palabras: [0.0, 0.58, 0.98]},
		cita: {archivo: 'ejemplo/cita.wav', dur: 3.18, palabras: [0.22, 0.84, 1.44, 1.68, 1.88]},
		opciones: {archivo: 'ejemplo/opciones.wav', dur: 3.46, palabras: [0.3, 0.46, 0.68, 1.42, 1.96, 2.18], tarjetas: [0, 3, 5]},
		autor: {archivo: 'ejemplo/autor.wav', dur: 4.04, palabras: [0.68, 1.16, 1.34, 2.22, 2.36, 2.58, 3.08], etiqueta: 5},
	},
};
