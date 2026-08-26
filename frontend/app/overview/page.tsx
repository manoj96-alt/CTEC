import { PageHeader } from "@/components/design-system/page-header";
import { OverviewCards } from "./_components/overview-cards";

export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Overview"
        title="Overview"
        description="Real, already-authorized CTEC activity across supplier risk, entity resolution, ontology governance, and connectors."
      />
      <OverviewCards />
    </div>
  );
}
