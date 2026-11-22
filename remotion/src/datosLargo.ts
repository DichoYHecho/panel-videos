/**
 * Datos del prototipo del vídeo largo (una pregunta de cada tipo). En producción saldrán del banco verificado
 * de Airtable y de Wikidata, como los Shorts. Aquí solo hay datos ya comprobados en el piloto:
 * Quevedo (1580-1645, Madrid; letrilla «Poderoso caballero es don Dinero», principios del s. XVII),
 * Simone de Beauvoir (1908-1986, París; «El segundo sexo», 1949) y Lope de Vega (1562-1635).
 */
import type {DatosQuizLargo} from './QuizLargo';

const QUEVEDO = {autor: 'Francisco de Quevedo', foto: 'ejemplo/quevedo.jpg', foco: [0.45, 0.45] as [number, number]};
const SIMONE = {autor: 'Simone de Beauvoir', foto: 'ejemplo/simone.jpg', foco: [0.55, 0.35] as [number, number]};
const LOPE = {nombre: 'Lope de Vega', foto: 'ejemplo/lope.jpg', foco: [0.42, 0.3] as [number, number], zoom: 1.5};

export const QUIZ_LARGO_PRUEBA: DatosQuizLargo = {
	titulo: '¿Quién lo dijo?',
	subtitulo: 'El gran quiz de las frases',
	total: 20,
	// Música variada creada con código (videos/musica_variada.py): una pista por tramo
	musica: {
		intro: 'ejemplo/musica/intro.wav',
		niveles: ['ejemplo/musica/facil.wav', 'ejemplo/musica/medio.wav', 'ejemplo/musica/dificil.wav', 'ejemplo/musica/dificil.wav'],
		final: 'ejemplo/musica/final.wav',
	},
	preguntas: [
		{
			nivel: 0,
			tipo: 'quien',
			cita: 'Poderoso caballero es *don* *Dinero.*',
			opciones: [
				LOPE,
				{nombre: 'Francisco de Quevedo', foto: 'ejemplo/quevedo.jpg', foco: [0.43, 0.47], zoom: 1.9},
				{nombre: 'Calderón de la Barca', foto: 'ejemplo/calderon.jpg', foco: [0.45, 0.35], zoom: 1.5},
			],
			correcta: 1,
			ficha: {...QUEVEDO, dato: 'Lo escribió en una letrilla satírica a principios del siglo XVII.'},
		},
		{
			nivel: 0,
			tipo: 'completa',
			antes: 'No se nace mujer: se llega a',
			opciones: ['saberlo', 'serlo', 'temerlo'],
			correcta: 1,
			ficha: {...SIMONE, dato: 'La frase está en «El segundo sexo», que publicó en 1949.'},
		},
		{
			nivel: 0,
			tipo: 'vf',
			cita: 'Poderoso caballero es don Dinero.',
			propuesto: LOPE,
			verdadero: false,
			ficha: {...QUEVEDO, dato: 'No es de Lope de Vega, sino de Quevedo, que escribió en la misma época.'},
		},
		{
			nivel: 1,
			tipo: 'pais',
			paises: [
				{nombre: 'España', id: '724', ciudad: 'Madrid', lon: -3.7033, lat: 40.4169, bandera: 'ejemplo/banderas/es.svg'},
				{nombre: 'Francia', id: '250', ciudad: 'París', lon: 2.3522, lat: 48.8566, bandera: 'ejemplo/banderas/fr.svg'},
				{nombre: 'Argentina', id: '032', ciudad: 'Buenos Aires', lon: -58.3816, lat: -34.6037, bandera: 'ejemplo/banderas/ar.svg'},
			],
			correcta: 1,
			ficha: {...SIMONE, dato: 'Nació en París en 1908 y murió allí en 1986.'},
		},
		{
			nivel: 1,
			tipo: 'siglo',
			opciones: [
				{rotulo: 's. XV', desde: 1400, hasta: 1500},
				{rotulo: 's. XVII', desde: 1600, hasta: 1700},
				{rotulo: 's. XIX', desde: 1800, hasta: 1900},
			],
			correcta: 1,
			vida: {nace: 1580, muere: 1645},
			ficha: {...QUEVEDO, dato: 'Vivió entre 1580 y 1645, en pleno Siglo de Oro.'},
		},
		{
			nivel: 2,
			tipo: 'pistas',
			pistas: [
				{icono: '🕰️', texto: 'Siglo XX'},
				{icono: '📍', texto: 'Francia'},
				{icono: '✒️', texto: 'Escritora y filósofa'},
			],
			recorte: 'ejemplo/simone_recorte.png',
			proporcion: 689 / 516,
			ficha: {...SIMONE, dato: 'Escribió «El segundo sexo» (1949).'},
		},
	],
};
