import type { AssessmentDraft } from "./contracts";
export function validateAssessment(
  value: AssessmentDraft,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [key, item] of Object.entries(value))
    if (typeof item === "string" && !item.trim()) errors[key] = "Required";
  for (const key of [
    "identityScore",
    "semanticScore",
    "assertionScore",
    "knowledgeScore",
    "decisionScore",
    "governanceScore",
  ] as const)
    if (value[key] < 0 || value[key] > 1)
      errors[key] = "Enter a value from 0 to 1";
  return errors;
}
