import { CapabilityStatusBadge } from "@/components/design-system/capability-status-badge";
import { PageHeader } from "@/components/design-system/page-header";
import { ContextIdentifiersProvider } from "@/lib/context/context-provider";
import { ContextLookup } from "./_components/context-lookup";

export default function Page() {
  return (
    <div className="max-w-5xl">
      <PageHeader
        eyebrow="Context"
        title="Context Explorer"
        description="Resolve the governed coverage and evidence-availability status of a single information element on a specific blueprint."
        action={<CapabilityStatusBadge status="SUPPORTED_NOW" />}
      />
      <ContextIdentifiersProvider>
        <ContextLookup />
      </ContextIdentifiersProvider>
    </div>
  );
}
