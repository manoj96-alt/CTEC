import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import type { User } from "oidc-client-ts";
import { SessionControls } from "@/components/session-controls";

const {
  accessTokenMock,
  observeSessionLossMock,
  sessionManagerMock,
  signInMock,
  signOutMock,
  stopObservingMock,
  usePathnameMock,
} = vi.hoisted(() => ({
  accessTokenMock: vi.fn(),
  observeSessionLossMock: vi.fn(),
  sessionManagerMock: vi.fn(),
  signInMock: vi.fn(),
  signOutMock: vi.fn(),
  stopObservingMock: vi.fn(),
  usePathnameMock: vi.fn(),
}));

vi.mock("@/lib/auth/browser-session", () => ({
  accessToken: accessTokenMock,
  observeSessionLoss: observeSessionLossMock,
  sessionManager: sessionManagerMock,
  signIn: signInMock,
  signOut: signOutMock,
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
}));

type UserLoadedCallback = (user: User) => void;
type UserUnloadedCallback = () => void;

function fakeUser(expired: boolean): User {
  return { expired } as User;
}

let userLoadedCallback: UserLoadedCallback | null;
let userUnloadedCallback: UserUnloadedCallback | null;
let unsubscribeLoadedMock: ReturnType<typeof vi.fn>;
let unsubscribeUnloadedMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  accessTokenMock.mockReset();
  observeSessionLossMock.mockReset();
  signInMock.mockReset();
  signOutMock.mockReset();
  stopObservingMock.mockReset();
  sessionManagerMock.mockReset();
  usePathnameMock.mockReset();

  observeSessionLossMock.mockReturnValue(stopObservingMock);
  signInMock.mockResolvedValue(undefined);
  signOutMock.mockResolvedValue(undefined);
  usePathnameMock.mockReturnValue("/quality");

  userLoadedCallback = null;
  userUnloadedCallback = null;
  unsubscribeLoadedMock = vi.fn();
  unsubscribeUnloadedMock = vi.fn();

  sessionManagerMock.mockReturnValue({
    events: {
      addUserLoaded: vi.fn((cb: UserLoadedCallback) => {
        userLoadedCallback = cb;
        return unsubscribeLoadedMock;
      }),
      addUserUnloaded: vi.fn((cb: UserUnloadedCallback) => {
        userUnloadedCallback = cb;
        return unsubscribeUnloadedMock;
      }),
    },
  });
});

// 1. Anonymous initial state -> Sign in visible, Sign out absent.
test("renders Sign in on an anonymous initial state", async () => {
  accessTokenMock.mockResolvedValue(null);
  render(<SessionControls />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("button", { name: "Sign out" }),
  ).not.toBeInTheDocument();
});

test("renders nothing when the auth configuration itself is missing (no session possible)", async () => {
  sessionManagerMock.mockImplementation(() => {
    throw new Error("Browser authentication configuration is incomplete");
  });
  const { container } = render(<SessionControls />);
  await waitFor(() => expect(sessionManagerMock).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
  expect(accessTokenMock).not.toHaveBeenCalled();
});

// 2. Existing authenticated session on initial mount -> Sign out visible.
test("renders Sign out when a session already exists on mount", async () => {
  accessTokenMock.mockResolvedValue("a-real-access-token");
  render(<SessionControls />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );
});

// 3. Sign-in completed after mount (userLoaded) -> Sign out appears, no remount.
test("a userLoaded event after mount makes Sign out appear, without remounting", async () => {
  accessTokenMock.mockResolvedValue(null);
  render(<SessionControls />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );

  expect(userLoadedCallback).not.toBeNull();
  userLoadedCallback?.(fakeUser(false));

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );
});

// 4. Logout/session-loss (userUnloaded) -> Sign out disappears.
test("a userUnloaded event clears an authenticated Sign out control", async () => {
  accessTokenMock.mockResolvedValue("a-real-access-token");
  render(<SessionControls />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );

  expect(userUnloadedCallback).not.toBeNull();
  userUnloadedCallback?.();

  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Sign out" }),
    ).not.toBeInTheDocument(),
  );
});

// 5. Clicking Sign out calls the existing shared signOut().
test("clicking Sign out calls the shared signOut()", async () => {
  accessTokenMock.mockResolvedValue("a-real-access-token");
  render(<SessionControls />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
  expect(signOutMock).toHaveBeenCalledTimes(1);
});

test("clears the control when a cross-tab session-loss signal is observed", async () => {
  let onLoss: () => void = () => {};
  observeSessionLossMock.mockImplementation((callback: () => void) => {
    onLoss = callback;
    return stopObservingMock;
  });
  accessTokenMock.mockResolvedValue("a-real-access-token");
  render(<SessionControls />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );
  onLoss();
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Sign out" }),
    ).not.toBeInTheDocument(),
  );
});

// 6. Listener cleanup occurs on unmount.
test("unsubscribes userLoaded/userUnloaded and stops observing session loss on unmount", async () => {
  accessTokenMock.mockResolvedValue(null);
  const { unmount } = render(<SessionControls />);
  await waitFor(() => expect(accessTokenMock).toHaveBeenCalled());
  unmount();
  expect(unsubscribeLoadedMock).toHaveBeenCalledTimes(1);
  expect(unsubscribeUnloadedMock).toHaveBeenCalledTimes(1);
  expect(stopObservingMock).toHaveBeenCalledTimes(1);
});

// 7. A stale initial async result cannot overwrite a newer userLoaded event.
test("a slower stale initial check cannot overwrite a newer userLoaded event", async () => {
  let resolveAccessToken: (token: string | null) => void = () => {};
  accessTokenMock.mockImplementation(
    () =>
      new Promise<string | null>((resolve) => {
        resolveAccessToken = resolve;
      }),
  );
  render(<SessionControls />);
  await waitFor(() => expect(accessTokenMock).toHaveBeenCalled());

  // The event arrives first, while the initial check is still in flight.
  expect(userLoadedCallback).not.toBeNull();
  userLoadedCallback?.(fakeUser(false));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );

  // The stale initial check then resolves with a contradicting, outdated
  // result -- it must not undo the live state established above.
  resolveAccessToken(null);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );
});

// 8. Clicking Sign in calls the shared signIn() with the current pathname.
test("clicking Sign in calls the shared signIn() with the current pathname", async () => {
  usePathnameMock.mockReturnValue("/quality");
  accessTokenMock.mockResolvedValue(null);
  render(<SessionControls />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(signInMock).toHaveBeenCalledTimes(1);
  expect(signInMock).toHaveBeenCalledWith("/quality");
});

// 9. Session-loss latch: a stale userLoaded arriving after userUnloaded
// must not resurrect Sign out.
test("after a userUnloaded loss signal, a later stale userLoaded cannot restore Sign out", async () => {
  accessTokenMock.mockResolvedValue("a-real-access-token");
  render(<SessionControls />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument(),
  );

  userUnloadedCallback?.();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );

  // A stray/late userLoaded (e.g. a bounded-renewal attempt that was
  // already in flight when the loss occurred) must not undo the loss.
  userLoadedCallback?.(fakeUser(false));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("button", { name: "Sign out" }),
  ).not.toBeInTheDocument();
});

// 10. Session-loss latch: a stale initial accessToken() resolution arriving
// after a cross-tab logout signal must not resurrect Sign out.
test("after a cross-tab session-loss signal, a slower stale initial accessToken() result cannot restore Sign out", async () => {
  let onLoss: () => void = () => {};
  observeSessionLossMock.mockImplementation((callback: () => void) => {
    onLoss = callback;
    return stopObservingMock;
  });
  let resolveAccessToken: (token: string | null) => void = () => {};
  accessTokenMock.mockImplementation(
    () =>
      new Promise<string | null>((resolve) => {
        resolveAccessToken = resolve;
      }),
  );
  render(<SessionControls />);
  await waitFor(() => expect(accessTokenMock).toHaveBeenCalled());

  // The cross-tab loss signal arrives first, while the initial check is
  // still in flight.
  onLoss();
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );

  // The stale initial check then resolves as if the user were signed in --
  // it must not undo the already-observed loss.
  resolveAccessToken("a-real-access-token");
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("button", { name: "Sign out" }),
  ).not.toBeInTheDocument();
});
