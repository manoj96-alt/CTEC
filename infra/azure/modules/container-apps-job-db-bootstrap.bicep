// CDD-068: one-time (or credential-rotation-time) ADMIN-authority database
// bootstrap Job. Runs inside the existing, already-private Container Apps
// Environment/VNet -- gains PostgreSQL reachability solely because it
// executes there, no new network resource of any kind.
//
// BINDING INVARIANT (CDD-068 SS14/SS20 item 6): this module contains ZERO
// Key Vault secretRef/secret-URI dependencies of any kind. All credentials
// it needs are delivered exclusively via @secure() Bicep deployment
// parameters, surfaced to the container as plain (non-Key-Vault-backed)
// Container Apps secrets. This is what breaks the circular dependency --
// not merely relocates it: the six Key Vault application secrets do not
// need to exist for this Job to run, and this Job never reads Key Vault.
//
// Self-contained managed identity: deliberately NOT id-migration and NOT
// any identity from managed-identities.bicep -- CDD-068 requires BOOTSTRAP,
// MIGRATION, and APPLICATION authority to remain structurally distinct,
// never the same Azure identity. This identity receives AcrPull only (to
// pull its own image) -- no Key Vault role of any kind, confirmed absent
// below.
metadata description = 'CDD-068: private, ADMIN-authority, one-time database bootstrap Container Apps Job'

@description('Job name, e.g. noetva-dev-eus2-db-bootstrap')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment resource ID (already private/VNet-integrated)')
param environmentId string

@description('ACR resource ID, for scoping this Job identity\'s AcrPull role assignment only')
param acrId string

@description('ACR login server')
param acrLoginServer string

@description('Full bootstrap image reference (registry/repo@sha256:digest). MUST be a digest, never a mutable tag -- identical trust policy to every other Noetva image.')
param imageReference string

@description('PostgreSQL Flexible Server FQDN (non-secret; the private DNS-resolvable hostname)')
param postgresHost string

@description('PostgreSQL administrator login name (non-secret, fixed architectural constant, matches modules/postgresql.bicep\'s own default)')
param postgresAdminUser string = 'noetva_pg_admin'

@secure()
@description('PostgreSQL administrator (break-glass ADMIN authority) password. Bounded to this one bootstrap run -- never persisted to Key Vault by this module, never read from Key Vault.')
param postgresAdminPassword string

@secure()
@description('Password to (re)set for the noetva_app application role. The operator uses this SAME value when separately populating the ctec-database-url Key Vault secret -- this module never reads or writes that secret itself.')
param postgresAppPassword string

@secure()
@description('Password to (re)set for the noetva_migrate migration role. The operator uses this SAME value when separately populating the ctec-migration-database-url Key Vault secret -- this module never reads or writes that secret itself.')
param postgresMigratePassword string

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

// The ONLY role this identity ever receives: pull its own image. No Key
// Vault role of any kind is assigned here or anywhere else in this module.
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, identity.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource dbBootstrapJob 'Microsoft.App/jobs@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 300
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: acrLoginServer
          identity: identity.id
        }
      ]
      // Plain, non-Key-Vault-backed Container Apps secrets only -- Azure
      // encrypts these at rest and never exposes them again via the
      // Portal/API after this deployment sets them. This is the exact
      // mechanism that lets the bootstrap credential chain never touch
      // Key Vault (CDD-068 SS11/SS12/SS14).
      secrets: [
        { name: 'pg-admin-password', value: postgresAdminPassword }
        { name: 'pg-app-password', value: postgresAppPassword }
        { name: 'pg-migrate-password', value: postgresMigratePassword }
      ]
    }
    template: {
      containers: [
        {
          name: 'db-bootstrap'
          image: imageReference
          env: [
            { name: 'NOETVA_PG_HOST', value: postgresHost }
            { name: 'NOETVA_PG_ADMIN_USER', value: postgresAdminUser }
            { name: 'NOETVA_PG_ADMIN_PASSWORD', secretRef: 'pg-admin-password' }
            { name: 'NOETVA_PG_APP_PASSWORD', secretRef: 'pg-app-password' }
            { name: 'NOETVA_PG_MIGRATE_PASSWORD', secretRef: 'pg-migrate-password' }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

output jobId string = dbBootstrapJob.id
output jobName string = dbBootstrapJob.name
output identityPrincipalId string = identity.properties.principalId
