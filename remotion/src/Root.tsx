import React from 'react';
import {Composition, Still} from 'remotion';
import {Quiz, duracionQuiz} from './Quiz';
import {Miniatura, type DatosMiniatura} from './Miniatura';
import {EJEMPLO, type DatosQuiz} from './datos';
import {QuizLargo, duracionQuizLargo, type DatosQuizLargo} from './QuizLargo';
import {QUIZ_LARGO_PRUEBA} from './datosLargo';
import {LoDijo, duracionLoDijo, type DatosLoDijo} from './LoDijo';
import {LODIJO_EINSTEIN} from './datosLoDijo';
import {ContraAutor, duracionContra, type DatosContra} from './ContraAutor';
import {CONTRA_MUERTE} from './datosContra';
import {Origen, duracionOrigen, type DatosOrigen} from './Origen';
import {ORIGEN_OJO} from './datosOrigen';

const MINIATURA_EJEMPLO: DatosMiniatura = {foto: 'ejemplo/simone.jpg', recorte: 'ejemplo/simone_recorte.png', proporcion: 689 / 516, tema: 'coraje', cabeza: [0.57, 0.38]};

// Los datos de cada vídeo llegan con --props (los prepara videos/quiz.py); los EJEMPLO solo sirven para el Studio.
export const Root: React.FC = () => (
	<>
		<Composition
			id="Quiz"
			component={Quiz}
			defaultProps={EJEMPLO}
			durationInFrames={duracionQuiz(EJEMPLO)}
			calculateMetadata={({props}) => ({durationInFrames: duracionQuiz(props as DatosQuiz)})}
			fps={30}
			width={1080}
			height={1920}
		/>
		<Still id="Miniatura" component={Miniatura} defaultProps={MINIATURA_EJEMPLO} width={1080} height={1920} />
		<Composition
			id="QuizLargo"
			component={QuizLargo}
			defaultProps={QUIZ_LARGO_PRUEBA}
			durationInFrames={duracionQuizLargo(QUIZ_LARGO_PRUEBA)}
			calculateMetadata={({props}) => ({durationInFrames: duracionQuizLargo(props as DatosQuizLargo)})}
			fps={30}
			width={1920}
			height={1080}
		/>
		{/* prototipo fase 2 (27 nov 2026) */}
		<Composition
			id="LoDijo"
			component={LoDijo}
			defaultProps={LODIJO_EINSTEIN}
			durationInFrames={duracionLoDijo(LODIJO_EINSTEIN)}
			calculateMetadata={({props}) => ({durationInFrames: duracionLoDijo(props as DatosLoDijo)})}
			fps={30}
			width={1080}
			height={1920}
		/>
		<Composition
			id="ContraAutor"
			component={ContraAutor}
			defaultProps={CONTRA_MUERTE}
			durationInFrames={duracionContra(CONTRA_MUERTE)}
			calculateMetadata={({props}) => ({durationInFrames: duracionContra(props as DatosContra)})}
			fps={30}
			width={1080}
			height={1920}
		/>
		<Composition
			id="Origen"
			component={Origen}
			defaultProps={ORIGEN_OJO}
			durationInFrames={duracionOrigen(ORIGEN_OJO)}
			calculateMetadata={({props}) => ({durationInFrames: duracionOrigen(props as DatosOrigen)})}
			fps={30}
			width={1080}
			height={1920}
		/>
	</>
);
