import type { Metadata } from "next";
import { AssessmentForm } from "@/components/supplier-risk/assessment-form";
export const metadata: Metadata = {
  title: "New supplier-risk assessment · CTEC",
};
export default function NewAssessmentPage() {
  return <AssessmentForm />;
}
