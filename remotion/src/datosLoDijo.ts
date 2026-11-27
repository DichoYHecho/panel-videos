import type {DatosLoDijo} from './LoDijo';
import voz from '../public/proto/lodijo_einstein_v3.json';

// Prototipo «¿Lo dijo o no lo dijo?» v3 (27 nov 2026). Origen verificado: Quote Investigator (2017) y Chequeado;
// «The Ultimate Quotable Einstein» (Princeton, 2010, p. 474) la incluye entre las atribuidas erróneamente.
// Einstein: 14 mar 1879 – 18 abr 1955. Las fuentes NO salen en el vídeo: van en la descripción.
// Fotos: dominio público (Wikimedia Commons). Tiempos de escena medidos sobre las pausas reales de la voz.
export const LODIJO_EINSTEIN: DatosLoDijo = {
	foto: 'proto/einstein.jpg', // Orren Jack Turner, 1947
	foco: [0.5, 0.3],
	fotoNodo: 'proto/einstein.jpg',
	autor: 'Albert Einstein',
	cita: 'La *locura* es hacer lo mismo una y otra vez y esperar resultados diferentes.',
	veredicto: 'falso',
	voz: {archivo: 'proto/lodijo_einstein_v3.wav', dur: voz.dur, palabras: voz.palabras},
	musica: 'proto/musica_lodijo.wav',
	citaIdx: [10, 23],
	gancho: {a: '¿Sabías que esta frase de Einstein…', b: 'nunca la dijo Einstein?', tB: 2.35},
	t: {cita: 4.9, veredicto: 10.6, origen: 11.45, anio: 13.6, doc: 15.3, autorNodo: 17.55, vida0: 18.6, vida1: 20.1, murio: 22.05, anios: 22.34, pregunta: 25.25},
	origen: {anio: 1981, doc: 'Narcóticos Anónimos', docSub: 'folleto', nace: 1879, muere: 1955},
	pregunta: '¿Tú también creías que era *suya*?',
};
