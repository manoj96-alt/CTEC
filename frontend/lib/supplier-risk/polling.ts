export function nextPollDelay(attempt: number): number {
  return Math.min(30_000, 5_000 * Math.max(1, attempt));
}
export function shouldPoll(state: string, visible = true): boolean {
  return visible && ["Accepted", "Executing"].includes(state);
}
