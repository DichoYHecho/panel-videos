import type {DatosOrigen} from './Origen';
import voz from '../public/proto/origen_ojo_v1.json';

// Prototipo «El origen» v1 (27 nov 2026): «ojo por ojo». Verificado (las fuentes van en la descripción):
// - Código de Hammurabi, Babilonia, h. 1754 a. C., ley 196 (a quien saca un ojo a otro, se le saca un ojo).
// - La ley del talión fijaba un castigo proporcional: no mayor que el daño.
// - Éxodo 21, 24 («ojo por ojo, diente por diente»); Mateo 5, 38-39 («a cualquiera que te hiera en la mejilla
//   derecha, vuélvele también la otra»).
// Sin fotos: estela, ojos, libro y rostro dibujados en SVG. Tiempos medidos sobre las pausas reales de la voz.
export const ORIGEN_OJO: DatosOrigen = {
	expresion: 'Ojo por ojo',
	voz: {archivo: 'proto/origen_ojo_v1.wav', dur: voz.dur, palabras: voz.palabras},
	musica: 'proto/musica_origen.wav',
	gancho: {a: 'no nació para pedir venganza…', b: 'sino para ponerle límite?', tB: 4.2},
	pais: {nombre: 'actual Irak', id: '368', ciudad: 'Babilonia', lon: 44.42, lat: 32.54},
	t: {mapa: 6.55, anios: 7.6, estela: 9.0, lugar: 10.28, ley: 11.4, ley2: 13.32, idea: 15.4, linea: 19.0, pregunta: 28.0},
	hace: 'Hace casi 4.000 años',
	ley: {rotulo: 'Ley 196', a: 'si le sacas un ojo a otro…', b: '…te sacarán un ojo a ti'},
	hitos: [
		{titulo: 'Hammurabi', sub: 'Babilonia · h. 1754 a. C.', icono: 'estela', t: 19.0},
		{titulo: 'Éxodo', sub: 'la Biblia', icono: 'libro', frase: 'ojo por ojo, diente por diente', t: 20.2},
		{titulo: 'Jesús', sub: 'los Evangelios', icono: 'mejilla', frase: 'pon la otra mejilla', t: 22.45},
	],
	pregunta: '¿Tú qué crees que es más justo?',
	opciones: ['Ojo por ojo', 'Poner la otra mejilla'],
};
