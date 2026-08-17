import { afterEach, beforeEach, expect, test, vi } from "vitest";

const { removeUserMock, signoutRedirectMock, broadcastPostMessageMock } =
  vi.hoisted(() => ({
    removeUserMock: vi.fn(),
    signoutRedirectMock: vi.fn(),
    broadcastPostMessageMock: vi.fn(),
  }));

let callOrder: string[] = [];
let constructedChannelNames: string[] = [];

vi.mock("oidc-client-ts", () => {
  class FakeUserManager {
    events = {
      addUserLoaded: vi.fn(() => vi.fn()),
      addUserUnloaded: vi.fn(() => vi.fn()),
    };
    async removeUser(...args: unknown[]): Promise<void> {
      callOrder.push("removeUser");
      await removeUserMock(...args);
    }
    async signoutRedirect(...args: unknown[]): Promise<void> {
      callOrder.push("signoutRedirect");
      await signoutRedirectMock(...args);
    }
  }
  class FakeWebStorageStateStore {}
  return {
    UserManager: FakeUserManager,
    WebStorageStateStore: FakeWebStorageStateStore,
  };
});

// jsdom does not implement BroadcastChannel, and Vitest's real (Node)
// BroadcastChannel does not reliably deliver across instances inside its
// test isolation context -- verified separately with a standalone probe.
// Actual cross-tab delivery is exercised by the live Playwright browser
// E2E flow instead; here we verify the *contract*: signOut() posts
// "logout" on the exact channel name observeSessionLoss subscribes to.
class FakeBroadcastChannel {
  name: string;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  constructor(name: string) {
    this.name = name;
    constructedChannelNames.push(name);
  }
  postMessage(data: unknown): void {
    broadcastPostMessageMock(this.name, data);
  }
  close(): void {}
}

const OIDC_ENV: Record<string, string> = {
  NEXT_PUBLIC_OIDC_AUTHORITY: "http://localhost:8081/realms/CTEC",
  NEXT_PUBLIC_OIDC_CLIENT_ID: "ctec-frontend",
  NEXT_PUBLIC_OIDC_REDIRECT_URI: "http://localhost:3000/auth/callback",
  NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI: "http://localhost:3000/",
  NEXT_PUBLIC_CTEC_API_ORIGIN: "http://localhost:8000",
};
const originalEnv = Object.fromEntries(
  Object.keys(OIDC_ENV).map((key) => [key, process.env[key]]),
);

beforeEach(() => {
  for (const [key, value] of Object.entries(OIDC_ENV)) process.env[key] = value;
  callOrder = [];
  constructedChannelNames = [];
  removeUserMock.mockReset();
  signoutRedirectMock.mockReset();
  broadcastPostMessageMock.mockReset();
  removeUserMock.mockResolvedValue(undefined);
  signoutRedirectMock.mockResolvedValue(undefined);
  vi.stubGlobal("BroadcastChannel", FakeBroadcastChannel);
  vi.resetModules();
});

afterEach(() => {
  for (const key of Object.keys(OIDC_ENV)) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
  vi.unstubAllGlobals();
});

test("an authenticated signOut() invokes the OIDC signout redirect, and does not remove the user itself beforehand", async () => {
  const { signOut } = await import("@/lib/auth/browser-session");
  await signOut();
  expect(signoutRedirectMock).toHaveBeenCalledTimes(1);
  // The implementation itself must never call removeUser() before
  // signoutRedirect(): signoutRedirect() derives id_token_hint from the
  // still-present user and removes it internally at the correct point.
  expect(callOrder).toEqual(["signoutRedirect"]);
});

test("no token/user object is exposed to a caller of signOut()", async () => {
  const { signOut } = await import("@/lib/auth/browser-session");
  const result = await signOut();
  expect(result).toBeUndefined();
});

test("signOut() broadcasts a logout signal on the same channel name observeSessionLoss subscribes to", async () => {
  const { signOut, observeSessionLoss } =
    await import("@/lib/auth/browser-session");
  const stop = observeSessionLoss(() => {});
  const observerChannelName = constructedChannelNames.at(-1);
  expect(observerChannelName).toBeTruthy();

  await signOut();

  expect(broadcastPostMessageMock).toHaveBeenCalledWith(
    observerChannelName,
    "logout",
  );
  stop();
});

test("a signoutRedirect() failure clears the local session and rejects deterministically", async () => {
  signoutRedirectMock.mockRejectedValue(new Error("network failure"));
  const { signOut } = await import("@/lib/auth/browser-session");
  await expect(signOut()).rejects.toThrow("network failure");
  expect(callOrder).toEqual(["signoutRedirect", "removeUser"]);
});

test("signOut() still broadcasts logout even when signoutRedirect() subsequently fails", async () => {
  signoutRedirectMock.mockRejectedValue(new Error("network failure"));
  const { signOut, observeSessionLoss } =
    await import("@/lib/auth/browser-session");
  const stop = observeSessionLoss(() => {});
  const observerChannelName = constructedChannelNames.at(-1);

  await expect(signOut()).rejects.toThrow();

  expect(broadcastPostMessageMock).toHaveBeenCalledWith(
    observerChannelName,
    "logout",
  );
  stop();
});
