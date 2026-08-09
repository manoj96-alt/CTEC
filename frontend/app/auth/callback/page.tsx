"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { completeSignIn } from "@/lib/auth/browser-session";
export default function AuthCallback() {
  const router = useRouter();
  const [error, setError] = useState("");
  useEffect(() => {
    completeSignIn()
      .then(({ returnPath }) => {
        history.replaceState({}, "", location.pathname);
        router.replace(returnPath);
      })
      .catch(() =>
        setError(
          "Authentication could not be completed. Please sign in again.",
        ),
      );
  }, [router]);
  return (
    <main role="status">
      <h1>{error ? "Sign-in failed" : "Completing sign-in"}</h1>
      <p>{error || "Validating the trusted identity response…"}</p>
    </main>
  );
}
