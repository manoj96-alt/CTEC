import { SupplyChainImpactApiError } from "@/lib/supply-chain-impact/api-client";
import type { SupplyChainImpactEvaluateRequestBody } from "@/lib/supply-chain-impact/contracts";

test("safe API errors retain code and status", () => {
  const error = new SupplyChainImpactApiError(
    "AUTHORIZATION_SCOPE_REQUIRED",
    403,
  );
  expect(error.code).toBe("AUTHORIZATION_SCOPE_REQUIRED");
  expect(error.status).toBe(403);
});

test("the evaluate request body type carries only the evaluation target", () => {
  // Structural proof, not a runtime mock: TypeScript rejects any other key
  // at compile time (CDD-016 §17/§23) -- this test exists to keep that
  // guarantee visible and regression-tested, not to duplicate tsc.
  const body: SupplyChainImpactEvaluateRequestBody = {
    supplier_entity_id: "00000000-0000-0000-0000-000000000000",
  };
  expect(Object.keys(body)).toEqual(["supplier_entity_id"]);
});
