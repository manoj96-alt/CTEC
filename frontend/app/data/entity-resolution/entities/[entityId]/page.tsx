"use client";

import { useParams } from "next/navigation";
import { ResolvedEntityDetail } from "./_components/resolved-entity-detail";

export default function Page() {
  const params = useParams<{ entityId: string }>();
  return (
    <div className="max-w-5xl">
      <ResolvedEntityDetail key={params.entityId} entityId={params.entityId} />
    </div>
  );
}
