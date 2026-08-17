"use client";

import { useEffect, useState } from "react";
import {
  accessToken,
  observeSessionLoss,
  sessionManager,
  signOut,
} from "@/lib/auth/browser-session";

export function SessionControls() {
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    let active = true;
    // Set by the userLoaded/userUnloaded handlers below: once either has
    // fired, the (slower, now-stale) initial accessToken() check below must
    // not overwrite the live state they establish.
    let liveStateObserved = false;

    let manager;
    try {
      manager = sessionManager();
    } catch {
      // Browser auth is not configured (e.g. NEXT_PUBLIC_OIDC_* unset) --
      // there is no session to observe.
      return;
    }

    const unsubscribeLoaded = manager.events.addUserLoaded((user) => {
      liveStateObserved = true;
      if (active) setSignedIn(!user.expired);
    });
    const unsubscribeUnloaded = manager.events.addUserUnloaded(() => {
      liveStateObserved = true;
      if (active) setSignedIn(false);
    });

    accessToken()
      .then((token) => {
        if (active && !liveStateObserved) setSignedIn(token !== null);
      })
      .catch(() => {
        // Browser auth is not configured or the session lookup otherwise
        // failed -- either way there is no session to sign out of.
        if (active && !liveStateObserved) setSignedIn(false);
      });

    const stopObserving = observeSessionLoss(() => {
      if (active) setSignedIn(false);
    });

    return () => {
      active = false;
      unsubscribeLoaded();
      unsubscribeUnloaded();
      stopObserving();
    };
  }, []);

  if (!signedIn) return null;

  return (
    <button type="button" className="button" onClick={() => void signOut()}>
      Sign out
    </button>
  );
}
