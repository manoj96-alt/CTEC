// Least-privilege user-assigned managed identities, one per distinct
// authority (Noetva D0 Section X / Noetva I0-R1 Section 13). Never one
// shared identity for multiple purposes.
metadata description = 'User-assigned managed identities for Noetva Azure runtime'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('GitHub repository in owner/repo form, used only for the federated credential subject')
param githubRepository string

@description('GitHub Actions environment name this identity is federated to (e.g. production)')
param githubEnvironmentName string

resource idFrontend 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-frontend'
  location: location
  tags: tags
}

resource idBackend 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-backend'
  location: location
  tags: tags
}

resource idMigration 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-migration'
  location: location
  tags: tags
}

resource idCicd 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-cicd'
  location: location
  tags: tags
}

// GitHub Actions OIDC workload-identity federation -- no AZURE_CLIENT_SECRET
// of any kind is ever stored (Noetva D0 Section AB / I0-R1 Section 14).
// Scoped to one GitHub Actions "environment" (e.g. production), which
// GitHub itself gates behind manual approval (configured on the GitHub
// side, not representable in Bicep -- see AX manual-input register).
resource cicdFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: idCicd
  name: 'github-${githubEnvironmentName}'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:environment:${githubEnvironmentName}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

output frontendIdentityId string = idFrontend.id
output frontendIdentityPrincipalId string = idFrontend.properties.principalId
output frontendIdentityClientId string = idFrontend.properties.clientId

output backendIdentityId string = idBackend.id
output backendIdentityPrincipalId string = idBackend.properties.principalId
output backendIdentityClientId string = idBackend.properties.clientId

output migrationIdentityId string = idMigration.id
output migrationIdentityPrincipalId string = idMigration.properties.principalId
output migrationIdentityClientId string = idMigration.properties.clientId

output cicdIdentityId string = idCicd.id
output cicdIdentityPrincipalId string = idCicd.properties.principalId
output cicdIdentityClientId string = idCicd.properties.clientId
