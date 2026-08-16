/** Legacy helpers — prefer flowCatalog for new code. */
import { emptyStartFlow, fullDefaultFlow, LABELS } from './flowCatalog'

export { emptyStartFlow, fullDefaultFlow, LABELS }

/** @deprecated Use canvas + flowCatalog instead of questionnaire-built flows. */
export function buildFlowFromAnswers() {
  return fullDefaultFlow()
}

export function boothModeFromAnswers() {
  return 'both'
}
