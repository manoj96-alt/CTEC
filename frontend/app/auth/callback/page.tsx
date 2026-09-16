"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ErrorResponse } from "oidc-client-ts";
import {
  authDiagnostics,
  completeSignIn,
  safeReturnPath,
} from "@/lib/auth/browser-session";

// CDD-082: safe, narrow diagnostic capture for the live-reproducible
// "Sign-in failed" callback defect under investigation (WOW-I3-A-R3).
// Activates only on the existing failure branch -- the success path and
// the silent-renewal branch below are byte-for-byte unchanged. Never
// renders or persists a code, token, verifier, nonce, state value, or
// the callback URL/query string itself -- only a sanitized library
// error class/message (oidc-client-ts's own error/error_description
// fields are standard, non-secret OAuth protocol strings by
// specification), a coarse phase marker, and boolean invocation/
// duplicate-consumption/silent-renewal signals. The duplicate-
// consumption check uses a one-way SHA-256 digest of the query string
// as its storage key -- the raw query string is never itself stored.
type DiagnosticInfo = {
  phase: string;
  errorClass: string;
  errorMessage: string;
  invocationCount: number;
  duplicateConsumption: boolean;
  silentRenewalAttempted: boolean;
};

const DUPLICATE_MARKER_PREFIX = "ctec-auth-callback-consumed-";

export async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function classifyCallbackFailure(failure: unknown): {
  phase: string;
  errorClass: string;
  errorMessage: string;
} {
  if (failure instanceof ErrorResponse) {
    return {
      phase: "AUTH_CALLBACK_TOKEN_EXCHANGE_OR_REDIRECT_ERROR",
      errorClass: "ErrorResponse",
      errorMessage: `${failure.error}${failure.error_description ? `: ${failure.error_description}` : ""}`,
    };
  }
  const message = failure instanceof Error ? failure.message : String(failure);
  if (
    message.includes("No matching state found in storage") ||
    message.includes("No state in response")
  ) {
    return {
      phase: "AUTH_CALLBACK_STATE_LOOKUP",
      errorClass: failure instanceof Error ? failure.name : "Unknown",
      errorMessage: message,
    };
  }
  return {
    phase: "AUTH_CALLBACK_UNKNOWN",
    errorClass: failure instanceof Error ? failure.name : "Unknown",
    errorMessage: message,
  };
}

export default function AuthCallback() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [diagnostic, setDiagnostic] = useState<DiagnosticInfo | null>(null);
  const invocationCount = useRef(0);

  useEffect(() => {
    invocationCount.current += 1;
    const thisInvocation = invocationCount.current;
    let cancelled = false;

    async function run() {
      const hash = await sha256Hex(location.search);
      const key = DUPLICATE_MARKER_PREFIX + hash;
      const duplicateConsumption = sessionStorage.getItem(key) === "1";
      sessionStorage.setItem(key, "1");

      try {
        const { returnPath } = await completeSignIn();
        if (cancelled) return;
        history.replaceState({}, "", location.pathname);
        router.replace(returnPath);
      } catch (failure: unknown) {
        if (cancelled) return;
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
        const { phase, errorClass, errorMessage } =
          classifyCallbackFailure(failure);
        setDiagnostic({
          phase,
          errorClass,
          errorMessage,
          invocationCount: thisInvocation,
          duplicateConsumption,
          silentRenewalAttempted: authDiagnostics().silentRenewalAttempted,
        });
        setError(
          "Authentication could not be completed. Please sign in again.",
        );
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main role="status">
      <h1>{error ? "Sign-in failed" : "Completing sign-in"}</h1>
      <p>{error || "Validating the trusted identity response…"}</p>
      {diagnostic ? (
        <dl
          data-testid="auth-callback-diagnostic"
          style={{ fontFamily: "monospace", fontSize: "0.85rem" }}
        >
          <dt>Phase</dt>
          <dd>{diagnostic.phase}</dd>
          <dt>Error class</dt>
          <dd>{diagnostic.errorClass}</dd>
          <dt>Error message</dt>
          <dd>{diagnostic.errorMessage}</dd>
          <dt>Invocation count (this mount)</dt>
          <dd>{diagnostic.invocationCount}</dd>
          <dt>Duplicate consumption detected</dt>
          <dd>{String(diagnostic.duplicateConsumption)}</dd>
          <dt>Silent renewal attempted this session</dt>
          <dd>{String(diagnostic.silentRenewalAttempted)}</dd>
        </dl>
      ) : null}
    </main>
  );
}
