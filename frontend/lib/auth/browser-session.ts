"use client";
import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";
import { browserAuthConfig } from "./config";

let manager: UserManager | null = null;
const channelName = "ctec-auth-lifecycle";
export function sessionManager(): UserManager {
  if (manager) return manager;
  const config = browserAuthConfig();
  manager = new UserManager({
    authority: config.authority,
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    post_logout_redirect_uri: config.postLogoutRedirectUri,
    response_type: "code",
    scope: config.scope,
    userStore: new WebStorageStateStore({ store: memoryStore() }),
    stateStore: new WebStorageStateStore({ store: sessionStorage }),
    automaticSilentRenew: false,
  });
  return manager;
}
export async function accessToken(): Promise<string | null> {
  const user = await sessionManager().getUser();
  return user && !user.expired ? user.access_token : null;
}
export async function signIn(returnPath = "/supplier-risk"): Promise<void> {
  const safe =
    returnPath.startsWith("/") && !returnPath.startsWith("//")
      ? returnPath
      : "/supplier-risk";
  await sessionManager().signinRedirect({ state: { returnPath: safe } });
}
export async function completeSignIn(): Promise<{
  user: User;
  returnPath: string;
}> {
  const user = await sessionManager().signinRedirectCallback();
  const state = user.state as { returnPath?: string } | undefined;
  const path = state?.returnPath;
  return {
    user,
    returnPath:
      path?.startsWith("/") && !path.startsWith("//") ? path : "/supplier-risk",
  };
}
export async function signOut(): Promise<void> {
  // Broadcast first: signoutRedirect() below navigates the browser away,
  // which can interrupt anything after it.
  new BroadcastChannel(channelName).postMessage("logout");
  try {
    // signoutRedirect() itself loads the current user, derives
    // id_token_hint from it, and only then removes it -- calling
    // removeUser() ourselves beforehand (as this used to do) discards the
    // ID token first, so Keycloak never receives id_token_hint and falls
    // back to an interactive "Do you want to log out?" confirmation
    // instead of completing RP-initiated logout silently.
    await sessionManager().signoutRedirect();
  } catch (error) {
    // signoutRedirect() failed before the browser navigated away (e.g. it
    // could not reach Keycloak's end-session endpoint). Clear the local
    // session directly so CTEC does not keep presenting an authenticated
    // UI indefinitely, then propagate the failure to the caller.
    await sessionManager().removeUser();
    throw error;
  }
}
export function observeSessionLoss(onLoss: () => void): () => void {
  const channel = new BroadcastChannel(channelName);
  channel.onmessage = () => onLoss();
  return () => channel.close();
}
function memoryStore(): Storage {
  const data = new Map<string, string>();
  return {
    length: 0,
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => {
      data.delete(k);
    },
    setItem: (k, v) => {
      data.set(k, v);
    },
  };
}
