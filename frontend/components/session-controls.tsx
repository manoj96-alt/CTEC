"use client";

import { useEffect, useState } from "react";
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
