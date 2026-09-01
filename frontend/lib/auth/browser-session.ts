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
// AUTH-UX-G: the only same-origin, non-open-redirect path CTEC will ever
// navigate back to after any sign-in (explicit or bounded-renewal). Shared
// by signIn() and the bounded-renewal path below so the safety check is
// defined exactly once.
export function safeReturnPath(candidate: unknown): string {
  return typeof candidate === "string" &&
    candidate.startsWith("/") &&
    !candidate.startsWith("//")
    ? candidate
    : "/supplier-risk";
}
function currentSafePath(): string {
  return typeof window === "undefined"
    ? "/supplier-risk"
    : safeReturnPath(window.location.pathname);
}
// AUTH-UX-I-R: a module-level flag alone is insufficient, because the
// bounded-renewal round trip itself (origin page -> Keycloak -> /auth
// /callback) is a full top-level navigation that destroys and recreates
// this entire JS module -- including this flag -- and /auth/callback is
// itself wrapped by the same root layout as every other page, so its own
// fresh mount could otherwise re-enter this exact function and start a
// second, independent renewal before the first one has even finished being
// processed (VM's discovered redirect-loop risk). sessionStorage survives
// that full-page reload without ever holding a token, an ID, or any secret
// -- it is a single boolean fact ("a bounded renewal round trip is already
// under way or has already failed for this browser tab"), the same class
// of non-token OIDC transaction-correlation data BSP-001 already permits
// for stateStore. It is never read as, and never contains, authentication
// or authorization material.
const RENEWAL_MARKER_KEY = "ctec-auth-bounded-renewal";
function renewalMarkerSet(): boolean {
  return (
    typeof window !== "undefined" &&
    sessionStorage.getItem(RENEWAL_MARKER_KEY) === "1"
  );
}
function setRenewalMarker(): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(RENEWAL_MARKER_KEY, "1");
  }
}
function clearRenewalMarker(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(RENEWAL_MARKER_KEY);
  }
}
// AUTH-UX-G bounded renewal: at most one prompt=none top-level Authorization
// Code + PKCE attempt per browser-tab lifecycle (see RENEWAL_MARKER_KEY
// above for why a per-module flag alone cannot enforce this), never
// signinSilent() (blocked by this app's own frozen frame-ancestors 'none'
// CSP -- BSP-001 still requires memory-only tokens, so there is no iframe
// involved at all). This flag is intentionally not exported: it is pure
// internal one-shot bookkeeping, not authentication or authorization state.
let renewalAttempted = false;
// AUTH-UX-G shared lifecycle: the single place accessToken()/principalId()
// obtain a currently-usable User. A missing or expired in-memory User
// triggers at most one bounded renewal attempt per page lifetime; an
// expired User is never returned to any caller.
async function restoredUser(): Promise<User | null> {
  const sessionManagerInstance = sessionManager();
  const user = await sessionManagerInstance.getUser();
  if (user && !user.expired) {
    // A stale marker from an earlier failed attempt (e.g. in a different
    // tab, or before this valid user materialized) no longer applies.
    clearRenewalMarker();
    return user;
  }
  if (renewalAttempted || renewalMarkerSet()) return null;
  renewalAttempted = true;
  // Set before navigating away, not after detecting failure: this is what
  // makes the guard survive the full-page reload a fresh /auth/callback
  // mount causes, closing the exact race VM identified.
  setRenewalMarker();
  // BSP-001: "Renewal uses bounded OIDC authorization with PKCE; if silent
  // authorization is not supported or fails, explicit reauthentication is
  // required." prompt: "none" guarantees Keycloak either redirects back
  // instantly with a fresh code (valid SSO session) or instantly with
  // error=login_required/interaction_required (no SSO session) -- it never
  // renders an interactive page, so this never surfaces an unexpected login
  // form. state.silent lets the existing /auth/callback distinguish this
  // from an explicit signIn() failure (see that file's own comment).
  await sessionManagerInstance
    .signinRedirect({
      prompt: "none",
      state: { returnPath: currentSafePath(), silent: true },
    })
    .catch(() => {
      // signinRedirect() itself failed to even initiate navigation (e.g. a
      // metadata/discovery failure) -- fail closed exactly like any other
      // bounded-renewal failure; there is nothing further to do here.
    });
  return null;
}
export async function accessToken(): Promise<string | null> {
  const user = await restoredUser();
  return user ? user.access_token : null;
}
// OQI-UX CDD-045 companion §4: the sole trustworthy identity claim for a
// governed decision. Mirrors the backend's own `oidc_subject_claim = "sub"`
// (TrustedPrincipal.principal_id) and Gate S's existing
// `requested_by=principal.principal_id` precedent -- never
// preferred_username/email/name, and never free text.
export async function principalId(): Promise<string | null> {
  const user = await restoredUser();
  if (!user) return null;
  const sub = user.profile.sub;
  return typeof sub === "string" && sub.length > 0 ? sub : null;
}
export async function signIn(returnPath = "/supplier-risk"): Promise<void> {
  // A deliberate user action always gets a clean slate -- the automatic-
  // renewal suppression marker must never block an explicit sign-in.
  clearRenewalMarker();
  await sessionManager().signinRedirect({
    state: { returnPath: safeReturnPath(returnPath) },
  });
}
export async function completeSignIn(): Promise<{
  user: User;
  returnPath: string;
}> {
  const user = await sessionManager().signinRedirectCallback();
  // A fresh, validated User -- whether from an explicit sign-in or a
  // successful bounded renewal -- means any earlier suppression no longer
  // applies.
  clearRenewalMarker();
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
