// Separate subscription-scoped entry point for Noetva's SHARED lifecycle
// control-plane resources (Noetva I-R2 Section 9/11): the lifecycle state
// Storage Table and the lifecycle automation identity are used ACROSS
// dev/staging/demo collectively, not duplicated per-environment inside
// each environment's own resource group. Deliberately does NOT modify
// R1's main.bicep/resources.bicep -- this is a new, additive composition
// root, exactly matching the "preserve R1, extend don't regenerate"
// instruction.
targetScope = 'subscription'

metadata description = 'Noetva lifecycle control-plane -- shared state storage and automation identity'

@description('Azure region')
param location string = 'eastus2'

@description('Naming prefix for lifecycle control-plane resources, e.g. noetva-lifecycle-eus2')
param namePrefix string = 'noetva-lifecycle-eus2'

@description('GitHub repository in owner/repo form')
param githubRepository string

@description('GitHub Actions environment names federated to the shared lifecycle identity -- Noetva R4-DRG D2: one credential per name is created (modules/lifecycle-identity.bicep), matching every lifecycle workflow own per-environment job binding. Frozen default is exactly the three lifecycle-managed environments -- never a single shared name (that subject matches no real workflow run), never including production.')
param githubEnvironmentNames array = [
  'dev'
  'staging'
  'demo'
]

@description('Log Analytics workspace resource ID to send lifecycle storage diagnostics to. If empty, an environment-specific workspace ID must be supplied at deploy time -- lifecycle automation spans environments and does not own its own Log Analytics workspace by design.')
param logAnalyticsWorkspaceId string

@description('Resource group names of the already-deployed, lifecycle-managed environments the lifecycle identity needs its custom role assigned in. DEPLOYMENT ORDER DEPENDENCY, disclosed not hidden: these resource groups (created by R1s main.bicep for dev/staging/demo) must already exist before this template is deployed -- role assignments below target them by name via cross-resource-group module scope, which requires the target to already exist.')
param managedEnvironmentResourceGroupNames array = [
  'rg-noetva-dev'
  'rg-noetva-staging'
  'rg-noetva-demo'
]

var tags = {
  environment: 'lifecycle'
  application: 'noetva'
  'managed-by': 'bicep'
  purpose: 'cost-lifecycle-automation'
  'customer-facing': 'false'
}

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-noetva-lifecycle'
  location: location
  tags: tags
}

module storage 'modules/lifecycle-state-storage.bicep' = {
  name: 'lifecycle-state-storage'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalyticsWorkspaceId
  }
}

module identity 'modules/lifecycle-identity.bicep' = {
  name: 'lifecycle-identity'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
    tags: tags
    githubRepository: githubRepository
    githubEnvironmentNames: githubEnvironmentNames
  }
}

// Assign the least-privilege custom role to the lifecycle identity, scoped
// to each non-production environment resource group individually -- never
// subscription-wide (Noetva I-R2 Section 11).
module roleAssignments 'modules/lifecycle-role-assignment.bicep' = [for rgName in managedEnvironmentResourceGroupNames: {
  name: 'lifecycle-role-assignment-${rgName}'
  scope: resourceGroup(rgName)
  params: {
    principalId: identity.outputs.lifecycleIdentityPrincipalId
    roleDefinitionId: identity.outputs.lifecycleRoleId
  }
}]

output storageAccountName string = storage.outputs.storageAccountName
output tableName string = storage.outputs.tableName
output tableEndpoint string = storage.outputs.tableEndpoint
output lifecycleIdentityClientId string = identity.outputs.lifecycleIdentityClientId
output lifecycleRoleId string = identity.outputs.lifecycleRoleId
