export interface ReviewFormulaItem {
  label?: string;
  expression: string;
  note?: string;
}

export interface ReviewParameterItem {
  symbol: string;
  value: string;
  description?: string;
}

export interface ReviewListItem {
  text: string;
  note?: string;
}

export interface ExperimentReviewData {
  eyebrow?: string;
  title?: string;
  purpose: string;
  apparatus?: string[];
  procedure?: ReviewListItem[];
  formulas?: ReviewFormulaItem[];
  parameters?: ReviewParameterItem[];
  notes?: string[];
}
