// Resource-group-scoped composition of every Noetva Azure resource
// (Noetva D0 Section BM: Container Apps + PostgreSQL Flexible Server +
// Entra External ID + Key Vault + ACR + VNet/NAT + Log Analytics).
// Deployed by main.bicep into a resource group dedicated to one
// environment (dev | staging | prod | demo) -- production never shares
// state with any other environment (Noetva D0 Section AI).
targetScope = 'resourceGroup'

metadata description = 'Noetva Azure production architecture -- resource-group composition'

@description('Environment name: dev | staging | prod | demo')
@allowed([
  'dev'
  'staging'
  'prod'
  'demo'
])
param environmentName string

@description('Azure region')
param location string = 'eastus2'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Full backend image reference (registry/repo@sha256:digest). Must be an immutable digest, never a mutable tag (Noetva D0 Section O).')
param backendImageReference string

@description('Full frontend image reference (registry/repo@sha256:digest), built with THIS environments own NEXT_PUBLIC_OIDC_* build args (Noetva I0-R1 Section 28/W: frontend images are environment-specific, never promoted unchanged across environments).')
param frontendImageReference string

@description('Public hostname the frontend will eventually be reachable on (informational only in R1 -- no DNS/cert resource is created against a domain that does not yet exist, Noetva I0-R1 Section 33)')
param frontendHostname string = ''

@description('Public hostname the backend will eventually be reachable on (informational only in R1)')
param backendHostname string = ''

@description('OIDC issuer the backend trusts (Entra External ID tenant issuer URL once provisioned)')
param oidcIssuer string

@description('OIDC audience (API application ID URI)')
param oidcAudience string

@description('OIDC JWKS URL')
param oidcJwksUrl string

@description('CORS origin(s) allowed to call the backend -- must be the exact frontend origin, no wildcard in staging/prod (Noetva I0-R1 Section 29)')
param corsOrigins string

@description('ACR SKU: Basic (dev/demo) or Premium (staging/prod) -- Noetva G-R3 Section 7')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

@description('PostgreSQL compute SKU name')
param postgresSkuName string = 'Standard_B2s'

@description('PostgreSQL compute SKU tier')
param postgresSkuTier string = 'Burstable'

@description('PostgreSQL storage size in GiB')
param postgresStorageGb int = 32

@description('PostgreSQL backup retention in days')
param postgresBackupRetentionDays int = 14

@description('PostgreSQL HA mode: Disabled | ZoneRedundant')
param postgresHaMode string = 'Disabled'

@secure()
@description('PostgreSQL administrator (break-glass ADMIN authority) password, supplied at deploy time only, never committed')
param postgresAdminPassword string

@description('Whether to provision a NAT Gateway for deterministic egress (required staging/prod, optional dev)')
param enableNatGateway bool = true

@description('Backend min replica count')
param backendMinReplicas int = 1

@description('Backend max replica count')
param backendMaxReplicas int = 3

@description('Frontend min replica count')
param frontendMinReplicas int = 1

@description('Frontend max replica count')
param frontendMaxReplicas int = 3

@description('Log retention in days')
param logRetentionDays int = 30

@description('Alert notification email')
param alertEmail string

@description('GitHub repository in owner/repo form')
param githubRepository string

@description('GitHub Actions environment name federated for this Azure environment')
param githubEnvironmentName string

// Deterministic lifecycle/FinOps tags (Noetva G-R2 Section AG / I-R2
// Section 29), computed purely from `environmentName` -- no environment
// parameter file needed to change for this, and no free-text tag value is
// ever operator-entered.
var lifecycleTagsByEnvironment = {
  dev: { lifecyclePolicy: 'dormant-by-default', autoShutdown: 'true', purpose: 'engineering', customerFacing: 'false' }
  staging: { lifecyclePolicy: 'dormant-except-validation-window', autoShutdown: 'true', purpose: 'validation', customerFacing: 'false' }
  demo: { lifecyclePolicy: 'dormant-by-default-ttl', autoShutdown: 'true', purpose: 'demo', customerFacing: 'true' }
  prod: { lifecyclePolicy: 'always-on', autoShutdown: 'false', purpose: 'production', customerFacing: 'true' }
}
var lifecycleTags = lifecycleTagsByEnvironment[environmentName]

var tags = {
  environment: environmentName
  application: 'noetva'
  'managed-by': 'bicep'
  'lifecycle-policy': lifecycleTags.lifecyclePolicy
  'auto-shutdown': lifecycleTags.autoShutdown
  owner: 'noetva-engineering'
  purpose: lifecycleTags.purpose
  'customer-facing': lifecycleTags.customerFacing
  'cost-center': 'noetva-${environmentName}'
}

module identities 'modules/managed-identities.bicep' = {
  name: 'identities'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    githubRepository: githubRepository
    githubEnvironmentName: githubEnvironmentName
  }
}

module network 'modules/network.bicep' = {
  name: 'network'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    enableNatGateway: enableNatGateway
  }
}

module monitoringBootstrap 'modules/monitoring-workspace-only.bicep' = {
  name: 'monitoring-workspace-only'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    logRetentionDays: logRetentionDays
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    enablePurgeProtection: environmentName == 'prod'
    logAnalyticsWorkspaceId: monitoringBootstrap.outputs.logAnalyticsWorkspaceId
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    acrSku: acrSku
    logAnalyticsWorkspaceId: monitoringBootstrap.outputs.logAnalyticsWorkspaceId
  }
}

module postgres 'modules/postgresql.bicep' = {
  name: 'postgres'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    delegatedSubnetId: network.outputs.postgresSubnetId
    privateDnsZoneId: network.outputs.postgresPrivateDnsZoneId
    skuName: postgresSkuName
    skuTier: postgresSkuTier
    storageSizeGb: postgresStorageGb
    backupRetentionDays: postgresBackupRetentionDays
    highAvailabilityMode: postgresHaMode
    administratorPassword: postgresAdminPassword
  }
}

module containerAppsEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'container-apps-environment'
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    infrastructureSubnetId: network.outputs.containerAppsSubnetId
    logAnalyticsWorkspaceId: monitoringBootstrap.outputs.logAnalyticsWorkspaceId
    logAnalyticsCustomerId: monitoringBootstrap.outputs.logAnalyticsCustomerId
    logAnalyticsSharedKey: monitoringBootstrap.outputs.logAnalyticsSharedKey
  }
}

module roleAssignments 'modules/role-assignments.bicep' = {
  name: 'role-assignments'
  params: {
    acrId: acr.outputs.registryId
    keyVaultId: keyVault.outputs.keyVaultId
    frontendPrincipalId: identities.outputs.frontendIdentityPrincipalId
    backendPrincipalId: identities.outputs.backendIdentityPrincipalId
    migrationPrincipalId: identities.outputs.migrationIdentityPrincipalId
    cicdPrincipalId: identities.outputs.cicdIdentityPrincipalId
  }
}

var backendEnvVars = [
  { name: 'CTEC_ENVIRONMENT', value: environmentName == 'prod' ? 'production' : 'development' }
  { name: 'CTEC_LOG_LEVEL', value: 'INFO' }
  { name: 'CTEC_CORS_ORIGINS', value: corsOrigins }
  { name: 'CTEC_OIDC_ISSUER', value: oidcIssuer }
  { name: 'CTEC_OIDC_AUDIENCE', value: oidcAudience }
  { name: 'CTEC_OIDC_JWKS_URL', value: oidcJwksUrl }
  { name: 'CTEC_RUNTIME_HANDOFF_KEY_ID', value: 'primary' }
]

var backendSecretRefs = [
  { name: 'ctec-database-url', keyVaultUrl: '${keyVault.outputs.keyVaultUri}secrets/ctec-database-url' }
  { name: 'ctec-runtime-handoff-key', keyVaultUrl: '${keyVault.outputs.keyVaultUri}secrets/ctec-runtime-handoff-key' }
]

module backendApp 'modules/container-app.bicep' = {
  name: 'backend-app'
  params: {
    name: '${namePrefix}-backend'
    location: location
    tags: tags
    environmentId: containerAppsEnvironment.outputs.environmentId
    imageReference: backendImageReference
    managedIdentityId: identities.outputs.backendIdentityId
    acrLoginServer: acr.outputs.registryLoginServer
    targetPort: 8000
    // Bypasses docker-entrypoint.sh entirely -- starts uvicorn directly, no
    // migration, no seeding (Noetva I0-R1 Section 22/23 critical invariant).
    commandOverride: [
      'uvicorn'
      'app.main:app'
      '--host'
      '0.0.0.0'
      '--port'
      '8000'
    ]
    envVars: backendEnvVars
    keyVaultSecretRefs: backendSecretRefs
    minReplicas: backendMinReplicas
    maxReplicas: backendMaxReplicas
  }
}

module migrationJob 'modules/container-apps-job-migration.bicep' = {
  name: 'migration-job'
  params: {
    name: '${namePrefix}-migrate'
    location: location
    tags: tags
    environmentId: containerAppsEnvironment.outputs.environmentId
    imageReference: backendImageReference
    managedIdentityId: identities.outputs.migrationIdentityId
    acrLoginServer: acr.outputs.registryLoginServer
    envVars: []
    keyVaultSecretRefs: [
      { name: 'ctec-database-url', keyVaultUrl: '${keyVault.outputs.keyVaultUri}secrets/postgres-migration-role-password' }
    ]
  }
}

module frontendApp 'modules/container-app.bicep' = {
  name: 'frontend-app'
  params: {
    name: '${namePrefix}-frontend'
    location: location
    tags: tags
    environmentId: containerAppsEnvironment.outputs.environmentId
    imageReference: frontendImageReference
    managedIdentityId: identities.outputs.frontendIdentityId
    acrLoginServer: acr.outputs.registryLoginServer
    targetPort: 3000
    commandOverride: []
    envVars: []
    keyVaultSecretRefs: []
    minReplicas: frontendMinReplicas
    maxReplicas: frontendMaxReplicas
  }
}

module monitoringAlerts 'modules/monitoring-alerts-only.bicep' = {
  name: 'monitoring-alerts-only'
  params: {
    namePrefix: namePrefix
    tags: tags
    alertEmail: alertEmail
    postgresServerId: postgres.outputs.serverId
    migrationJobId: migrationJob.outputs.jobId
  }
}

// Lifecycle-aware alert suppression (Noetva G-R3 Section 10/11) -- only
// for lifecycle-managed environments. `prod` never receives this
// resource: it has no lifecycle workflows to toggle it, and its
// availability alerts must never be suppressible by construction, not
// merely by policy.
module lifecycleAlertSuppression 'modules/lifecycle-alert-suppression.bicep' = if (environmentName != 'prod') {
  name: 'lifecycle-alert-suppression'
  params: {
    namePrefix: namePrefix
    tags: tags
  }
}

output resourceGroupName string = resourceGroup().name
output backendFqdn string = backendApp.outputs.fqdn
output frontendFqdn string = frontendApp.outputs.fqdn
output natGatewayEgressIp string = network.outputs.natGatewayEgressIp
output acrLoginServer string = acr.outputs.registryLoginServer
output keyVaultUri string = keyVault.outputs.keyVaultUri
output postgresServerFqdn string = postgres.outputs.serverFqdn
output cicdIdentityClientId string = identities.outputs.cicdIdentityClientId
// Informational only (Noetva I0-R1 Section 33): no DNS/certificate resource
// is created against these hostnames since no real domain is authorized yet
// (D0 Section AU/T -- do not invent a production domain). Surfaced here so
// the operator can see, post-deploy, which hostname this environment's
// Container App FQDN (above) must eventually be mapped to via a CNAME plus
// a Container Apps custom-domain + managed-certificate binding.
output frontendHostnameTarget string = frontendHostname
output backendHostnameTarget string = backendHostname
