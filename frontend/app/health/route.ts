// CDD-070: frontend-local, dependency-free liveness/startup route. Exists
// solely so the frontend Container App has its own truthful health target
// for Azure's Startup/Liveness probes -- the shared container-app.bicep
// module previously hardcoded the backend's /health for every consumer,
// which never existed on the frontend and left its revision permanently
// Activating.
//
// Deliberately minimal: no backend call, no OIDC/Entra dependency, no
// database access, no auth. Must remain answerable before Entra SPA
// configuration exists and before any final custom domain is bound.
export async function GET() {
  return Response.json({ status: "healthy" });
}
