// Generic Container App module, instantiated once for frontend and once for
// backend (Noetva D0 Section N). The `command`/`args` override is the
// mechanism that satisfies the critical invariant from Noetva I0-R1 Section
// 23: the backend Container App must start ONLY `uvicorn`, never the
// image's own `docker-entrypoint.sh`, so it can never execute a migration
// on ordinary startup -- that authority belongs exclusively to the
// migration Container Apps Job (container-apps-job-migration.bicep). This
// override changes NO file in the image; it is a pure orchestrator-level
// entrypoint override, identical in kind to any `docker run --entrypoint`.
//
// Cost lifecycle (Noetva G-R2/I-R2): `minReplicas=0` is fully supported by
// this module's existing `scale` block and is set to 0 for dev/staging/demo
// in their own parameter files -- this lets the HTTP scale rule genuinely
// scale to zero on idle traffic while an environment is READY/IN_USE. This
// is deliberately NOT what makes an environment DORMANT, though: bare
// scale-to-zero can be woken by any inbound request (a bot, a health
// scanner, a stray browser tab), which is exactly the failure mode Noetva
// G-R2 Section 9 named. Governed DORMANT is a separate, explicit action
// the lifecycle workflows perform on top of this -- deactivating the
// Container App's active revision (`az containerapp revision deactivate`)
// -- which will NOT scale back up on its own no matter what traffic
// arrives, and requires an explicit `revision activate` to return to
// service. Nothing in this module's own Bicep properties represents that
// deactivated state; it is a runtime action the lifecycle workflows take
// against an already-deployed revision, not a template-time setting.
metadata description = 'Generic Container App (frontend or backend)'

@description('Container App name, e.g. noetva-prod-eus2-backend')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment resource ID')
param environmentId string

@description('Full image reference, e.g. <registry>.azurecr.io/noetva/backend@sha256:...  MUST be a digest, never a mutable tag, never `latest`.')
param imageReference string

@description('User-assigned managed identity resource ID for this app (ACR pull + optional Key Vault access)')
param managedIdentityId string

@description('ACR login server, used for the registry reference')
param acrLoginServer string

@description('Target port the container listens on')
param targetPort int

@description('Override the image ENTRYPOINT/CMD. Empty array = use the image default (frontend). Non-empty = exact command Azure invokes instead (backend: bypasses docker-entrypoint.shs migration path).')
param commandOverride array = []

@description('Plain (non-secret) environment variables')
param envVars array = []

@description('Secret environment variables, each {name, envName, keyVaultUrl} -- resolved via this Container App identity, never inlined (Noetva D0 Section W). `name` is the Container Apps secret / Key Vault reference identifier; `envName` is the container environment-variable name the application actually reads -- CDD-070: these are two distinct namespaces, never derived from one another algorithmically.')
param keyVaultSecretRefs array = []

@description('CDD-070: the container HTTP path this workload truthfully answers for Startup/Liveness probing. Required, no default -- every consumer of this shared module must declare its own truthful health path; the module must never assume one workload\'s (originally backend\'s /health) is correct for every consumer.')
param healthProbePath string

@description('Minimum replica count')
param minReplicas int = 1

@description('Maximum replica count')
param maxReplicas int = 3

@description('CPU cores per replica')
param cpuCores string = '0.5'

@description('Memory per replica')
param memory string = '1Gi'

@description('HTTP concurrent-request scaling threshold per replica')
param httpConcurrentRequests int = 50

var keyVaultSecrets = [for ref in keyVaultSecretRefs: {
  name: ref.name
  keyVaultUrl: ref.keyVaultUrl
  identity: managedIdentityId
}]

var secretEnvVars = [for ref in keyVaultSecretRefs: {
  name: ref.envName
  secretRef: ref.name
}]

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: keyVaultSecrets
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: name
          image: imageReference
          command: empty(commandOverride) ? null : commandOverride
          resources: {
            cpu: json(cpuCores)
            memory: memory
          }
          env: concat(envVars, secretEnvVars)
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: healthProbePath
                port: targetPort
              }
              initialDelaySeconds: 10
              periodSeconds: 15
            }
            {
              // Startup probe only -- NOT a dependency-aware readiness
              // check. CDD-070: healthProbePath is deliberately consumer-
              // supplied, never hardcoded here -- this module previously
              // assumed every consumer implements backend's /health, which
              // broke the frontend (no such route exists there). Each
              // consumer's own probe path must be shallow/dependency-free
              // (Noetva D0 Section K / I0-R1 Section 31): process-liveness
              // only, never a DB-aware or cross-service readiness check.
              type: 'Startup'
              httpGet: {
                path: healthProbePath
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: string(httpConcurrentRequests)
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output containerAppId string = containerApp.id
