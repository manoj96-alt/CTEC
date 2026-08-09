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
  await sessionManager().removeUser();
  new BroadcastChannel(channelName).postMessage("logout");
  await sessionManager().signoutRedirect();
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
