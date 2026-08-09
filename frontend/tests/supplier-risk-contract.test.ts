import { outcomeLabel } from "@/lib/supplier-risk/mappers";
import { nextPollDelay, shouldPoll } from "@/lib/supplier-risk/polling";
test("outcomes are presented without changing meaning", () => {
  expect(outcomeLabel("CONDITIONALLY_APPROVED")).toBe("conditionally approved");
  expect(outcomeLabel(null)).toBe("In progress");
});
test("polling is bounded and terminal aware", () => {
  expect(nextPollDelay(99)).toBe(30000);
  expect(shouldPoll("Executing")).toBe(true);
  expect(shouldPoll("Completed")).toBe(false);
  expect(shouldPoll("Executing", false)).toBe(false);
});
