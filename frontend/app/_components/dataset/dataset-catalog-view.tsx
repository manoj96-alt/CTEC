"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { loadDemoDataset } from "@/lib/demo/fixture-loader";
import { datasetCatalog } from "@/lib/demo/dataset-catalog";
import type { DemoDataset, ParsedFile } from "@/lib/demo/types";
import { DatasetFileCard } from "./dataset-file-card";
import { DatasetInspectionPanel } from "./dataset-inspection-panel";
import { DatasetRelationshipSummary } from "./dataset-relationship-summary";
import { DatasetValidationSummary } from "./dataset-validation-summary";

// Catalog order matches this field order exactly — verified by
// tests/dataset-catalog.test.tsx ("the catalog lists exactly the seven
// canonical files").
function parsedFilesInCatalogOrder(
  dataset: DemoDataset,
): ParsedFile<unknown>[] {
  return [
    dataset.suppliers,
    dataset.materials,
    dataset.products,
    dataset.facilities,
    dataset.supplyAgreements,
    dataset.riskEvents,
    dataset.revenueExposure,
  ];
}

export function DatasetCatalogView() {
  const [dataset, setDataset] = useState<DemoDataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadDemoDataset()
      .then((loaded) => {
        if (cancelled) return;
        setDataset(loaded);
        setSelectedFileName(datasetCatalog[0].fileName);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Could not load the sample dataset.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const parsedFiles = useMemo(
    () => (dataset ? parsedFilesInCatalogOrder(dataset) : []),
    [dataset],
  );

  const selectedEntry =
    datasetCatalog.find((e) => e.fileName === selectedFileName) ?? null;
  const selectedParsedFile =
    dataset && selectedEntry
      ? parsedFiles[datasetCatalog.indexOf(selectedEntry)]
      : null;

  return (
    <div>
      <p className="eyebrow">Sample Dataset</p>
      <h1 style={{ marginTop: "0.25rem" }}>Dataset</h1>
      <p style={{ color: "var(--muted)", maxWidth: "42rem" }}>
        These are the seven sample source files that drive the Supplier Risk
        demonstration. This is a fixed sample dataset, not a live enterprise
        data connection or production ingestion pipeline.
      </p>

      {loading && (
        <p role="status" style={{ marginTop: "1.5rem" }}>
          Loading sample dataset…
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: "var(--danger)", marginTop: "1.5rem" }}>
          {error}
        </p>
      )}

      {!loading && !error && !dataset && (
        <p style={{ color: "var(--muted)", marginTop: "1.5rem" }}>
          No dataset is currently loaded.
        </p>
      )}

      {dataset && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(19rem, 1fr))",
              gap: "1rem",
              marginTop: "1.5rem",
            }}
          >
            {datasetCatalog.map((entry, index) => (
              <DatasetFileCard
                key={entry.fileName}
                entry={entry}
                parsedFile={parsedFiles[index]}
                issueCount={
                  dataset.validationIssues.filter(
                    (issue) => issue.file === entry.fileName,
                  ).length
                }
                selected={entry.fileName === selectedFileName}
                onSelect={() => setSelectedFileName(entry.fileName)}
              />
            ))}
          </div>

          {selectedEntry && selectedParsedFile && (
            <div style={{ marginTop: "1.5rem" }}>
              <DatasetInspectionPanel
                entry={selectedEntry}
                parsedFile={selectedParsedFile}
              />
            </div>
          )}

          <div style={{ marginTop: "1.5rem" }}>
            <DatasetRelationshipSummary dataset={dataset} />
          </div>

          <div style={{ marginTop: "1.5rem" }}>
            <DatasetValidationSummary dataset={dataset} />
          </div>

          <div className="panel" style={{ textAlign: "center" }}>
            <p style={{ fontWeight: 700 }}>Ready to see it in action?</p>
            <Link
              href="/demo/supplier-risk"
              className="button"
              style={{ marginTop: "0.75rem" }}
            >
              Explore Supplier Risk
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
