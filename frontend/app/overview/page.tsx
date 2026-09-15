import { PageHeader } from "@/components/design-system/page-header";
import { EnterpriseUnderstandingPanel } from "./_components/enterprise-understanding-panel";
import { OverviewCards } from "./_components/overview-cards";

export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Overview"
        title="Overview"
        description="Governed enterprise understanding: what requires attention, and where to investigate next."
      />
      <EnterpriseUnderstandingPanel />
      <OverviewCards />
    </div>
  );
}
