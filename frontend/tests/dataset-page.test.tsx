import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DatasetCatalogView } from "@/app/_components/dataset/dataset-catalog-view";

const CSV_FIXTURES: Record<string, string> = {
  "suppliers.csv":
    "supplier_id,supplier_name,region_id,region_name,qualification_status,available_capacity_pct,activation_lead_time_days,unit_cost_index_pct\n" +
    "SUP-001,Apex Components,REG-EA,East Asia Logistics Region,Active,100,0,100\n" +
    "SUP-002,Nova Energy Systems,REG-NA,North America Logistics Region,Qualified,60,21,107\n",
  "materials.csv":
    "material_id,material_name,supplier_id,unit_cost_usd\nMAT-100,Battery Cell BX-100,SUP-001,42.50\n",
  "products.csv":
    "product_id,product_name,material_id,facility_id\nPROD-01,Atlas Pro Laptop,MAT-100,FAC-01\n",
  "facilities.csv":
    "facility_id,facility_name,region_id,region_name\nFAC-01,Seattle Assembly Plant,REG-NA,North America Logistics Region\n",
  "supply_agreements.csv":
    "agreement_id,material_id,supplier_id,sourcing_pct,terms\nSA-100,MAT-100,SUP-001,100,Single-source\n",
  "risk_events.csv":
    "risk_event_id,region_id,region_name,severity,description\nRE-001,REG-EA,East Asia Logistics Region,Severe,Severe regional logistics disruption\n",
  "revenue_exposure.csv": "product_id,annual_revenue_usd\nPROD-01,48000000\n",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      const fileName = String(input).split("/").pop() as string;
      const text = CSV_FIXTURES[fileName];
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(text),
      } as Response);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows all seven canonical files as buttons, with counts derived from the loaded fixtures", async () => {
  render(<DatasetCatalogView />);

  await waitFor(() => screen.getByRole("button", { name: /Suppliers/ }));

  const suppliersCard = screen.getByRole("button", { name: /Suppliers/ });
  const materialsCard = screen.getByRole("button", { name: /Materials/ });
  const productsCard = screen.getByRole("button", { name: /Products/ });
  const facilitiesCard = screen.getByRole("button", { name: /Facilities/ });
  const agreementsCard = screen.getByRole("button", {
    name: /Supply Agreements/,
  });
  const riskEventsCard = screen.getByRole("button", { name: /Risk Events/ });
  const revenueCard = screen.getByRole("button", {
    name: /Revenue Exposure/,
  });

  expect(suppliersCard).toBeInTheDocument();
  expect(materialsCard).toBeInTheDocument();
  expect(productsCard).toBeInTheDocument();
  expect(facilitiesCard).toBeInTheDocument();
  expect(agreementsCard).toBeInTheDocument();
  expect(riskEventsCard).toBeInTheDocument();
  expect(revenueCard).toBeInTheDocument();

  // suppliers.csv has 2 rows in this fixture — derived, not hardcoded.
  expect(within(suppliersCard).getByText(/2/)).toBeInTheDocument();
  expect(suppliersCard.textContent).toMatch(/2\s*records?\s*·\s*8\s*columns?/);
});

test("selecting a file shows its curated schema and real sample records without moving focus", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() => screen.getByRole("button", { name: /Materials/ }));

  const materialsCard = screen.getByRole("button", { name: /Materials/ });
  materialsCard.focus();
  fireEvent.click(materialsCard);

  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: /Materials/ }),
    ).toBeInTheDocument(),
  );

  // Focus stays on the button the user clicked — not moved into the panel.
  expect(document.activeElement).toBe(materialsCard);

  expect(screen.getByText("Battery Cell BX-100")).toBeInTheDocument();
  expect(materialsCard).toHaveAttribute(
    "aria-controls",
    "dataset-inspection-panel",
  );
});

test("shows two distinct relationship sections, and the scenario one is explicitly labeled as one sample, not comprehensive", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() => screen.getByText("Detected Relationship Keys"));

  expect(screen.getByText("Detected Relationship Keys")).toBeInTheDocument();
  expect(screen.getByText("Sample Scenario Relationships")).toBeInTheDocument();
  expect(
    screen.getByText(/not a comprehensive relationship map/),
  ).toBeInTheDocument();

  const relationshipSection = screen
    .getByText("Sample Scenario Relationships")
    .closest("section")!;
  expect(
    within(relationshipSection).getAllByText(/Apex Components/).length,
  ).toBeGreaterThan(0);
});

test("uses accurate validation status labels, not the word Valid, with a concise scope note", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() => screen.getByText("Dataset Validation"));

  const validationSection = screen
    .getByText("Dataset Validation")
    .closest("section")!;

  expect(
    within(validationSection).getByText("✓ No detected integrity issues"),
  ).toBeInTheDocument();
  expect(
    within(validationSection).queryByText(/^Valid$/),
  ).not.toBeInTheDocument();
  expect(
    within(validationSection).getByText(
      /checks for duplicate identifiers and broken references/,
    ),
  ).toBeInTheDocument();
});

test("the primary CTA points to the no-auth demo route, and no Dataset-local link points to the auth-gated route", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() =>
    screen.getByRole("link", { name: "Explore Supplier Risk" }),
  );

  const cta = screen.getByRole("link", { name: "Explore Supplier Risk" });
  expect(cta).toHaveAttribute("href", "/demo/supplier-risk");

  const productionLink = screen
    .queryAllByRole("link")
    .find((link) => link.getAttribute("href") === "/supplier-risk");
  expect(productionLink).toBeUndefined();
});

test("a fetch failure produces a useful error state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        text: () => Promise.resolve(""),
      } as Response),
    ),
  );
  render(<DatasetCatalogView />);

  await waitFor(() => screen.getByRole("alert"));
  expect(screen.getByRole("alert")).toHaveTextContent(/Failed to load/);
});

test("revenue_exposure.csv's product_id shows the combined primary+foreign key designation", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() => screen.getByRole("button", { name: /Revenue Exposure/ }));

  fireEvent.click(screen.getByRole("button", { name: /Revenue Exposure/ }));

  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: /Revenue Exposure/ }),
    ).toBeInTheDocument(),
  );

  expect(
    screen.getByText("Primary key · Foreign key → products.csv"),
  ).toBeInTheDocument();
});

test("schema and sample tables use the Dataset-local responsive class, not the stacking shared table-wrap", async () => {
  render(<DatasetCatalogView />);
  await waitFor(() => screen.getByRole("heading", { name: /Suppliers/ }));

  const panel = document.getElementById("dataset-inspection-panel")!;
  const wrappers = panel.querySelectorAll(".dataset-table-wrap");
  expect(wrappers.length).toBe(2);
  expect(panel.querySelectorAll(".table-wrap").length).toBe(0);

  // Headers must remain in the DOM (not conditionally omitted) so values
  // are never shown without a visible field label at any width.
  const headerCells = panel.querySelectorAll("thead th");
  expect(headerCells.length).toBeGreaterThan(0);
});
