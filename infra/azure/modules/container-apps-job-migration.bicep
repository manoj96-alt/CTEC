// Dedicated Container Apps Job: the ONLY thing in this architecture
// authorized to run `alembic upgrade head` (Noetva D0 Section Z / I0-R1
// Section 22). Uses the identical backend image, command OVERRIDDEN to run
// only the migration + the two PRODUCTION-REQUIRED idempotent seeders
// (OntologySeeder, BlueprintSeeder -- see infra/azure/README.md Section P
// for the evidence-based classification that excludes every demo_*_seeder
// module from this path). This is the exact same sequence
// docker-entrypoint.sh already runs today, truncated before its final
// `exec uvicorn` line -- no image file is modified, no new script is baked
// in; the sequence is supplied entirely via the Job's `command`/`args`.
metadata description = 'Migration Container Apps Job for Noetva'

@description('Job name, e.g. noetva-prod-eus2-migrate')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment resource ID')
param environmentId string

@description('Full image reference, e.g. <registry>.azurecr.io/noetva/backend@sha256:...  Must be the SAME digest deployed to the backend Container App for this revision.')
param imageReference string

@description('User-assigned managed identity resource ID for the migration authority (ACR pull + MIGRATION-role DB secret access only, Noetva D0 Section BG)')
param managedIdentityId string

@description('ACR login server')
param acrLoginServer string

@description('Secret environment variables, each {name, envName, keyVaultUrl} -- MUST reference the MIGRATION Postgres role credential, never the APPLICATION or ADMIN role (Noetva I0-R1 Section 20/21). CDD-070: `name` is the Container Apps secret / Key Vault reference identifier; `envName` is the container environment-variable name the application (Alembic/backend Settings) actually reads -- never derived from `name` algorithmically.')
param keyVaultSecretRefs array = []

@description('Plain (non-secret) environment variables')
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

// Exact reproduction of docker-entrypoint.sh's migration+seed phases only
// (see backend/docker-entrypoint.sh, unmodified) -- never the final
// `exec uvicorn` line. `set -e`: any step failing aborts the Job with a
// non-zero exit before touching the next step, matching the entrypoint
// script's own `set -e` discipline.
var migrationScript = '''
set -e
echo "[migration-job] running database migrations..."
python -m alembic upgrade head

echo "[migration-job] seeding ontology (idempotent, PRODUCTION REQUIRED)..."
python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.infrastructure.persistence.ontology_seed import OntologySeeder

settings = get_settings()
engine = create_engine(settings.database_url)
factory = sessionmaker(engine)
with factory() as session:
    summary = OntologySeeder(session).load()
    session.commit()
print(f'[migration-job] ontology seed: {summary}')
"

echo "[migration-job] seeding canonical Blueprint (idempotent, PRODUCTION REQUIRED)..."
python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder

settings = get_settings()
engine = create_engine(settings.database_url)
factory = sessionmaker(engine)
with factory() as session:
    summary = BlueprintSeeder(session).load()
    session.commit()
print(f'[migration-job] blueprint seed: {summary}')
"

echo "[migration-job] verifying migration head..."
python -m alembic -c alembic.ini heads
echo "[migration-job] done."
'''

resource migrationJob 'Microsoft.App/jobs@2024-03-01' = {
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
          name: 'migrate'
          image: imageReference
          command: [
            '/bin/sh'
            '-c'
            migrationScript
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

output jobId string = migrationJob.id
output jobName string = migrationJob.name
