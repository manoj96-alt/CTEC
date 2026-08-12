import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { datasetCatalog } from "@/lib/demo/dataset-catalog";

const DEMO_DATA_DIR = join(process.cwd(), "public", "demo-data");

function actualHeaders(fileName: string): string[] {
  const text = readFileSync(join(DEMO_DATA_DIR, fileName), "utf-8");
  return text.trim().split(/\r?\n/)[0].split(",");
}

test("the catalog lists exactly the seven canonical files", () => {
  const fileNames = datasetCatalog.map((entry) => entry.fileName);
  expect(fileNames).toEqual([
    "suppliers.csv",
    "materials.csv",
    "products.csv",
    "facilities.csv",
    "supply_agreements.csv",
    "risk_events.csv",
    "revenue_exposure.csv",
  ]);
});

describe.each(datasetCatalog)(
  "catalog entry for $fileName matches the real CSV header",
  (entry) => {
    test("declared columns exactly match the actual file header, in order", () => {
      const declaredFields = entry.columns.map((column) => column.field);
      expect(declaredFields).toEqual(actualHeaders(entry.fileName));
    });

    test("the declared primary key is one of the declared columns", () => {
      const fields = entry.columns.map((column) => column.field);
      expect(fields).toContain(entry.primaryKey);
    });

    test("every foreign_key column declares a relationship target", () => {
      for (const column of entry.columns) {
        if (column.role === "foreign_key") {
          expect(column.relationshipTarget).toBeTruthy();
        }
      }
    });

    test("the declared primary key column is marked as such (directly, or via isPrimaryKey if it's also a foreign key)", () => {
      const primaryKeyColumn = entry.columns.find(
        (column) => column.field === entry.primaryKey,
      );
      expect(primaryKeyColumn).toBeDefined();
      const isProperlyMarked =
        primaryKeyColumn!.role === "primary_key" ||
        primaryKeyColumn!.isPrimaryKey === true;
      expect(isProperlyMarked).toBe(true);
    });
  },
);
