"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

// Lightweight, frontend-only, identifiers-only cross-workspace context
// model (CDD-033 §25, §34; Artifact Authorization §5 item 13). Carries only
// the two identifiers Context Explorer's own resolve call actually
// returned -- never an authoritative domain object, never a second
// semantic model, never a Gate F <-> H-U join.
export interface ContextIdentifiers {
  blueprintId: string | null;
  informationElementRequirementId: string | null;
}

interface ContextIdentifiersValue extends ContextIdentifiers {
  setContextIdentifiers: (identifiers: ContextIdentifiers) => void;
}

const ContextIdentifiersContext = createContext<ContextIdentifiersValue | null>(
  null,
);

export function ContextIdentifiersProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [identifiers, setIdentifiers] = useState<ContextIdentifiers>({
    blueprintId: null,
    informationElementRequirementId: null,
  });

  const value = useMemo<ContextIdentifiersValue>(
    () => ({
      ...identifiers,
      setContextIdentifiers: setIdentifiers,
    }),
    [identifiers],
  );

  return (
    <ContextIdentifiersContext.Provider value={value}>
      {children}
    </ContextIdentifiersContext.Provider>
  );
}

export function useContextIdentifiers(): ContextIdentifiersValue {
  const value = useContext(ContextIdentifiersContext);
  if (!value) {
    throw new Error(
      "useContextIdentifiers must be used within a ContextIdentifiersProvider",
    );
  }
  return value;
}
