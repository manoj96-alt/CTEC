import { SupplierRiskApiError } from "@/lib/supplier-risk/api-client";
test("safe API errors retain stable code and status", () => {
  const error = new SupplierRiskApiError(
    {
      code: "RATE_LIMITED",
      message: "Try later",
      correlation_id: "id",
      retryable: true,
    },
    429,
  );
  expect(error.problem.code).toBe("RATE_LIMITED");
  expect(error.status).toBe(429);
});
