import type {DatosContra} from './ContraAutor';
import voz from '../public/proto/contra_muerte_v1.json';

// Prototipo «Autor contra autor» v1 (27 nov 2026). Citas verificadas (las fuentes van en la descripción):
// - Epicuro, «Carta a Meneceo» (Diógenes Laercio, X, 125), traducción fiel.
// - Quevedo, soneto «Amor constante más allá de la muerte», último verso.
// Fotos: busto de Epicuro (dominio público, Wikimedia Commons) y retrato de Quevedo (material del piloto).
// Tiempos de escena medidos sobre las pausas reales de la voz.
export const CONTRA_MUERTE: DatosContra = {
	tema: 'La muerte',
	a: {nombre: 'Epicuro', foto: 'proto/epicuro.jpg', foco: [0.5, 0.35], epoca: 'Grecia · s. III a. C.', cita: 'Mientras existimos, la *muerte* no está; y cuando llega la *muerte*, ya no existimos.', citaIdx: [17, 30]},
	b: {nombre: 'Quevedo', foto: 'proto/quevedo_sin_rotulo.jpg', foco: [0.44, 0.38], epoca: 'España · s. XVII', cita: 'Polvo serán, mas polvo *enamorado*.', citaIdx: [43, 47], desfase: 0.25},
	voz: {archivo: 'proto/contra_muerte_v1.wav', dur: voz.dur, palabras: voz.palabras},
	musica: 'proto/musica_contra.wav',
	gancho: {a: '¿Sabías que dos de las frases más famosas sobre la muerte…', b: 'dicen justo lo contrario?', tB: 4.0},
	t: {vs: 5.35, nombreA: 6.2, citaA: 7.95, nombreB: 14.1, citaB: 17.8, pregunta: 20.9},
	pregunta: '¿Y tú con quién estás?',
	cierre: 'Te leo en comentarios',
};
