import React from 'react';
import {Composition} from 'remotion';
import {Quiz, duracionQuiz} from './Quiz';
import {EJEMPLO, type DatosQuiz} from './datos';

// Los datos de cada vídeo llegan con --props (los prepara videos/quiz.py); EJEMPLO solo sirve para el Studio.
export const Root: React.FC = () => (
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
);
