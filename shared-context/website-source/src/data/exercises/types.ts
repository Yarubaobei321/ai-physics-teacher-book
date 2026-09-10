export type ExerciseDifficulty = '基础' | '中等' | '挑战' | '拓展';

export interface ExerciseChoice {
  id: string;
  label: string;
}

interface ExerciseBase {
  number: number;
  difficulty: ExerciseDifficulty;
  category: string;
  stem: string;
  explanation: string;
}

export interface SingleChoiceExercise extends ExerciseBase {
  kind: 'single';
  choices: ExerciseChoice[];
  answer: string;
}

export interface MultiChoiceExercise extends ExerciseBase {
  kind: 'multi';
  choices: ExerciseChoice[];
  answer: string[];
}

export interface FillBlank {
  id: string;
  label?: string;
  answer: string;
  alternates?: string[];
}

export interface FillExercise extends ExerciseBase {
  kind: 'fill';
  blanks: FillBlank[];
}

export interface OpenExercise extends ExerciseBase {
  kind: 'open';
}

export type Exercise =
  | SingleChoiceExercise
  | MultiChoiceExercise
  | FillExercise
  | OpenExercise;
