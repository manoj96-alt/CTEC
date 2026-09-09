// Least-privilege Azure RBAC role assignments (Noetva D0 Section BD /
// I0-R1 Section 13). Never one identity with broad rights; never Owner
// assigned to a runtime identity.
metadata description = 'Least-privilege RBAC role assignments for Noetva'

@description('ACR resource ID')
param acrId string

@description('Key Vault resource ID')
param keyVaultId string

@description('Frontend managed identity principal ID')
param frontendPrincipalId string

@description('Backend managed identity principal ID')
param backendPrincipalId string

@description('Migration managed identity principal ID')
param migrationPrincipalId string

@description('CI/CD managed identity principal ID')
param cicdPrincipalId string

// Well-known built-in role definition IDs (stable across all Azure tenants).
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: last(split(keyVaultId, '/'))
}

// ACR Pull: frontend, backend, migration -- pull only, never push (push is
// the build pipeline's own separate, narrower-scoped credential path).
resource acrPullFrontend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, frontendPrincipalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: frontendPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource acrPullBackend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, backendPrincipalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: backendPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource acrPullMigration 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, migrationPrincipalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: migrationPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets User (read-only secret access, never Key Vault
// Administrator): backend (runtime secrets) and migration (migration DB
// role secret) only. Frontend receives NO Key Vault access -- it has no
// runtime secret (Noetva D0 Section V: its OIDC config is build-time only).
resource kvSecretsUserBackend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultId, backendPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: backendPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource kvSecretsUserMigration 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultId, migrationPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: migrationPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// CI/CD identity: Contributor scoped to THIS resource group only -- never
// subscription-wide (Noetva D0 Section BD / I0-R1 Section 14). Declared
// here (not in resources.bicep) specifically because `cicdPrincipalId`
// arrives as a plain string PARAMETER of this module -- resolvable at the
// start of deployment -- rather than as a module-output property accessed
// inline in a sibling resource, which Bicep's role-assignment name
// resolution (BCP120) does not accept.
resource cicdContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, cicdPrincipalId, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: cicdPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output acrPullRoleId string = acrPullRoleId
output keyVaultSecretsUserRoleId string = keyVaultSecretsUserRoleId
output contributorRoleId string = contributorRoleId
