"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ErrorResponse } from "oidc-client-ts";
import { completeSignIn, safeReturnPath } from "@/lib/auth/browser-session";
export default function AuthCallback() {
  const router = useRouter();
  const [error, setError] = useState("");
  useEffect(() => {
    completeSignIn()
      .then(({ returnPath }) => {
        history.replaceState({}, "", location.pathname);
        router.replace(returnPath);
      })
      .catch((failure: unknown) => {
        // AUTH-UX-G: oidc-client-ts's own state-store-validated userState
        // (see ErrorResponse's constructor -- it is populated from the same
        // signed correlation record that protects the success path, before
        // the error is even inspected) is the only trustworthy way to tell
        // a bounded prompt=none renewal apart from an explicit signIn()
        // failure. A bounded-renewal failure (the user's Keycloak SSO
        // session is simply absent/expired) is not an authentication
        // "failure" from the user's point of view -- they never asked to
        // sign in -- so it must return them to their original page and let
        // that page's own normal unauthenticated state/Sign In control take
        // over, never the interactive error screen below.
        const state =
          failure instanceof ErrorResponse
            ? (failure.state as { returnPath?: unknown; silent?: unknown })
            : undefined;
        if (state?.silent === true) {
          history.replaceState({}, "", location.pathname);
          router.replace(safeReturnPath(state.returnPath));
          return;
        }
        setError(
          "Authentication could not be completed. Please sign in again.",
        );
      });
  }, [router]);
  return (
    <main role="status">
      <h1>{error ? "Sign-in failed" : "Completing sign-in"}</h1>
      <p>{error || "Validating the trusted identity response…"}</p>
    </main>
  );
}
