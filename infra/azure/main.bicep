// Subscription-scoped entry point: creates the environment's isolated
// resource group, then deploys the full Noetva Azure architecture into it
// (Noetva D0 Section BC: single subscription, isolated resource groups per
// environment at this stage of company maturity).
targetScope = 'subscription'

metadata description = 'Noetva Azure production architecture -- entry point'

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

@description('Full backend image reference (registry/repo@sha256:digest)')
param backendImageReference string

@description('Full frontend image reference (registry/repo@sha256:digest), built with this environments own OIDC build args')
param frontendImageReference string

param frontendHostname string = ''
param backendHostname string = ''

@description('OIDC issuer the backend trusts')
param oidcIssuer string

@description('OIDC audience')
param oidcAudience string

@description('OIDC JWKS URL')
param oidcJwksUrl string

@description('OAuth scope-claim name the backend trusts for delegated authorization (Entra External ID: scp; matches Noetva\'s Keycloak default of scope only if explicitly set otherwise).')
param oidcScopeClaim string

@description('JWT claim name carrying the Noetva business-tenant identifier (Entra External ID: a namespaced custom claim, since the bare name "tenant_id" is a Microsoft-reserved JWT claim; local Keycloak: tenant_id).')
param oidcTenantClaim string

@description('CORS origin(s) allowed to call the backend')
param corsOrigins string

@description('ACR SKU: Basic (dev/demo) or Premium (staging/prod) -- Noetva G-R3 Section 7')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

param postgresSkuName string = 'Standard_B2s'
param postgresSkuTier string = 'Burstable'
param postgresStorageGb int = 32
param postgresBackupRetentionDays int = 14
param postgresHaMode string = 'Disabled'

@secure()
param postgresAdminPassword string

param enableNatGateway bool = true
param backendMinReplicas int = 1
param backendMaxReplicas int = 3
param frontendMinReplicas int = 1
param frontendMaxReplicas int = 3
param logRetentionDays int = 30
param alertEmail string
param githubRepository string
param githubEnvironmentName string

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-noetva-${environmentName}'
  location: location
  tags: {
    environment: environmentName
    application: 'noetva'
    'managed-by': 'bicep'
  }
}

module resources 'resources.bicep' = {
  name: 'noetva-${environmentName}-resources'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    namePrefix: namePrefix
    backendImageReference: backendImageReference
    frontendImageReference: frontendImageReference
    frontendHostname: frontendHostname
    backendHostname: backendHostname
    oidcIssuer: oidcIssuer
    oidcAudience: oidcAudience
    oidcJwksUrl: oidcJwksUrl
    oidcScopeClaim: oidcScopeClaim
    oidcTenantClaim: oidcTenantClaim
    corsOrigins: corsOrigins
    acrSku: acrSku
    postgresSkuName: postgresSkuName
    postgresSkuTier: postgresSkuTier
    postgresStorageGb: postgresStorageGb
    postgresBackupRetentionDays: postgresBackupRetentionDays
    postgresHaMode: postgresHaMode
    postgresAdminPassword: postgresAdminPassword
    enableNatGateway: enableNatGateway
    backendMinReplicas: backendMinReplicas
    backendMaxReplicas: backendMaxReplicas
    frontendMinReplicas: frontendMinReplicas
    frontendMaxReplicas: frontendMaxReplicas
    logRetentionDays: logRetentionDays
    alertEmail: alertEmail
    githubRepository: githubRepository
    githubEnvironmentName: githubEnvironmentName
  }
}

output resourceGroupName string = resources.outputs.resourceGroupName
output backendFqdn string = resources.outputs.backendFqdn
output frontendFqdn string = resources.outputs.frontendFqdn
output natGatewayEgressIp string = resources.outputs.natGatewayEgressIp
output acrLoginServer string = resources.outputs.acrLoginServer
output keyVaultUri string = resources.outputs.keyVaultUri
output postgresServerFqdn string = resources.outputs.postgresServerFqdn
output cicdIdentityClientId string = resources.outputs.cicdIdentityClientId
