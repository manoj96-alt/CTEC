import "@testing-library/jest-dom/vitest";
class TestBroadcastChannel {
  onmessage: (() => void) | null = null;
  postMessage() {}
  close() {}
}
Object.defineProperty(globalThis, "BroadcastChannel", {
  value: TestBroadcastChannel,
  writable: true,
});

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, "ResizeObserver", {
  value: TestResizeObserver,
  writable: true,
  configurable: true,
});
