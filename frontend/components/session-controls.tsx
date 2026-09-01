"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  accessToken,
  observeSessionLoss,
  sessionManager,
  signIn,
  signOut,
} from "@/lib/auth/browser-session";

export function SessionControls() {
  const pathname = usePathname();
  // This mount's effect intentionally runs once (see the [] deps below) and
  // must judge "am I mounting on /auth/callback" only at that moment -- the
  // component itself persists across later client-side route changes
  // (root-layout-mounted), and re-running this whole effect on every
  // navigation is a larger behavior change than this correction calls for.
  // A ref (not `pathname` itself) is the correct way to read a value once
  // without becoming a reactive effect dependency.
  const initialPathnameRef = useRef(pathname);
  const [signedIn, setSignedIn] = useState(false);
  // Distinct from `signedIn`: whether browser auth is configured at all
  // (e.g. NEXT_PUBLIC_OIDC_* present). Defaults to false so a misconfigured
  // deployment renders nothing -- never a "Sign in" control with nowhere
  // safe to go -- matching this component's pre-existing behavior for that
  // case exactly.
  const [authAvailable, setAuthAvailable] = useState(false);

  useEffect(() => {
    let active = true;
    // Set by the userLoaded/userUnloaded handlers below: once either has
    // fired, the (slower, now-stale) initial accessToken() check below must
    // not overwrite the live state they establish.
    let liveStateObserved = false;
    // AUTH-UX-G session-loss latch: once an authoritative loss signal
    // (userUnloaded, or a cross-tab logout broadcast) has been observed
    // during this mount, it is permanent for the remainder of the mount --
    // a later, stale userLoaded (e.g. from a bounded-renewal attempt that
    // was already in flight when the user signed out) or a late-resolving
    // initial accessToken() check must never resurrect the signed-in UI.
    // Only a fresh signIn() -- a new deliberate action, which itself causes
    // a fresh navigation and therefore a fresh mount -- may sign in again.
    let sessionLossObserved = false;

    let manager;
    try {
      manager = sessionManager();
    } catch {
      // Browser auth is not configured (e.g. NEXT_PUBLIC_OIDC_* unset) --
      // there is no session to observe.
      return;
    }
    // Set only from an async/event-callback boundary below, never
    // synchronously here in the effect body, matching the same pattern
    // already used for `signedIn`.
    const markAuthAvailable = () => {
      if (active) setAuthAvailable(true);
    };
    // sessionManager() succeeding already proves auth is configured --
    // independent of whether the accessToken() check below runs (it is
    // deliberately skipped on /auth/callback, see below), so this must not
    // depend on that check ever resolving. This component is mounted once
    // by the root layout and persists across client-side route changes
    // (e.g. /auth/callback -> the original page), so this is the only
    // chance this mount gets to establish authAvailable if it lands on
    // /auth/callback first.
    void Promise.resolve().then(markAuthAvailable);

    const unsubscribeLoaded = manager.events.addUserLoaded((user) => {
      liveStateObserved = true;
      markAuthAvailable();
      if (sessionLossObserved) return;
      if (active) setSignedIn(!user.expired);
    });
    const unsubscribeUnloaded = manager.events.addUserUnloaded(() => {
      liveStateObserved = true;
      sessionLossObserved = true;
      markAuthAvailable();
      if (active) setSignedIn(false);
    });

    // AUTH-UX-I-R: /auth/callback is the sole owner of processing the
    // active OIDC callback (via completeSignIn()/signinRedirectCallback()).
    // Because this component is mounted by the root layout on every route
    // including /auth/callback itself, an unconditional accessToken() call
    // here would independently race that in-flight processing and could
    // start its own second bounded-renewal redirect before the first one
    // finished being handled -- exactly the loop VM identified. The
    // userLoaded/userUnloaded listeners above stay active (they only
    // observe, never initiate), so a genuine sign-in completed by the
    // callback page is still reflected immediately.
    if (initialPathnameRef.current !== "/auth/callback") {
      accessToken()
        .then((token) => {
          markAuthAvailable();
          if (active && !liveStateObserved && !sessionLossObserved) {
            setSignedIn(token !== null);
          }
        })
        .catch(() => {
          // Browser auth is not configured or the session lookup otherwise
          // failed -- either way there is no session to sign out of.
          markAuthAvailable();
          if (active && !liveStateObserved && !sessionLossObserved) {
            setSignedIn(false);
          }
        });
    }

    const stopObserving = observeSessionLoss(() => {
      sessionLossObserved = true;
      markAuthAvailable();
      if (active) setSignedIn(false);
    });

    return () => {
      active = false;
      unsubscribeLoaded();
      unsubscribeUnloaded();
      stopObserving();
    };
  }, []);

  if (!authAvailable) return null;

  if (!signedIn) {
    return (
      <button
        type="button"
        className="button"
        onClick={() => void signIn(pathname)}
      >
        Sign in
      </button>
    );
  }

  return (
    <button type="button" className="button" onClick={() => void signOut()}>
      Sign out
    </button>
  );
}
