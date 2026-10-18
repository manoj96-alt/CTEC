// Dedicated Container Apps Job: the ONLY thing in this architecture
// authorized to run `golden-demo-restore`/`demo-verify` against the
// dedicated demo PostgreSQL server (CDD-087 §7/§13). Mirrors
// container-apps-job-migration.bicep's exact structure (same
// triggerType: Manual shape, same managed-identity/ACR-pull pattern) --
// the only two differences are the command (two database_cli.py
// subcommand invocations, not inline python -c blocks, because the
// restore/verify logic itself is complex enough to deserve real, tested
// Python rather than duplicated Bicep-embedded shell) and reusing the
// backend Container App's own managed identity/Key Vault secret
// (`ctec-database-url`, the noetva_app role -- CDD-087 §11: no new DB
// role, no new managed identity is authorized).
//
// This module is gated by its own independent `deployGoldenRestoreJob`
// boolean (CDD-087 §7), never nested inside `deployApplicationTier`,
// mirroring `deployDbBootstrapJob`'s own established independent-gating
// precedent exactly -- restore must be invokable even when the backend/
// frontend Container Apps are scaled to zero replicas.
metadata description = 'Golden Demo restore Container Apps Job for Noetva (CDD-087)'

@description('Job name, e.g. noetva-demo-eus2-golden-restore')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment resource ID')
param environmentId string

@description('Full image reference, e.g. <registry>.azurecr.io/noetva/backend@sha256:...  Must be the SAME digest deployed to the backend Container App for this revision.')
param imageReference string

@description('User-assigned managed identity resource ID -- reuses the backend Container App\'s own identity (ACR pull + noetva_app-role DB secret access only, CDD-087 §11), never a new identity.')
param managedIdentityId string

@description('ACR login server')
param acrLoginServer string

@description('Secret environment variables, each {name, envName, keyVaultUrl} -- MUST reference the APPLICATION (noetva_app) Postgres role credential (the same `ctec-database-url` secret the backend Container App already uses), never the MIGRATION or ADMIN role (CDD-087 §11).')
param keyVaultSecretRefs array = []

@description('Plain (non-secret) environment variables -- MUST include CTEC_ENVIRONMENT=demo, CTEC_GOLDEN_DEMO_RESTORE_ALLOWED=true, and CTEC_GOLDEN_RESTORE_EXPECTED_HOST set to the dedicated demo PostgreSQL server\'s own FQDN (CDD-087 §9 Checks 2/3).')
param envVars array = []

var keyVaultSecrets = [for ref in keyVaultSecretRefs: {
  name: ref.name
  keyVaultUrl: ref.keyVaultUrl
  identity: managedIdentityId
}]

var secretEnvVars = [for ref in keyVaultSecretRefs: {
  name: ref.envName
  secretRef: ref.name
}]

// CDD-087 §7: exactly two database_cli.py subcommand invocations, `set -e`
// so a restore failure aborts before verification ever runs (matching the
// migration Job's own `set -e` discipline exactly).
var goldenRestoreScript = '''
set -e
echo "[golden-restore-job] running Golden restore..."
python -m app.infrastructure.persistence.database_cli golden-demo-restore
echo "[golden-restore-job] running Golden verification..."
python -m app.infrastructure.persistence.database_cli demo-verify
echo "[golden-restore-job] done."
'''

resource goldenRestoreJob 'Microsoft.App/jobs@2024-03-01' = {
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
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 900
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: keyVaultSecrets
    }
    template: {
      containers: [
        {
          name: 'golden-restore'
          image: imageReference
          command: [
            '/bin/sh'
            '-c'
            goldenRestoreScript
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(envVars, secretEnvVars)
        }
      ]
    }
  }
}

output jobId string = goldenRestoreJob.id
output jobName string = goldenRestoreJob.name
