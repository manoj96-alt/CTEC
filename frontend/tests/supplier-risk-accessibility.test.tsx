import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import { RouteState } from "@/components/supplier-risk/route-state";
import { StatusSummary } from "@/components/supplier-risk/status-summary";
test("core status presentation has no automated accessibility violations", async () => {
  const { container } = render(
    <main>
      <RouteState title="Unavailable" message="Try again later" />
      <StatusSummary execution="Executing" outcome={null} stage="SRM" />
    </main>,
  );
  const results = await axe(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(results.violations).toHaveLength(0);
});
