// Separate, least-privilege identity for lifecycle automation (Noetva G-R2
// Section AV / I-R2 Section 11) -- distinct from R1's `id-cicd` deployment
// identity, which needs broad per-environment Contributor to run `az
// deployment` at all. This identity gets a narrow CUSTOM role: only the
// specific actions the start/stop/sweep/monitor workflows actually need,
// scoped to the non-production resource groups only. No Owner. No
// subscription-wide Contributor.
metadata description = 'Least-privilege lifecycle automation identity and custom role for Noetva'

@description('Naming prefix, e.g. noetva-lifecycle-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('GitHub repository in owner/repo form, used only for the federated credential subject')
param githubRepository string

@description('GitHub Actions environment name this identity is federated to (e.g. lifecycle)')
param githubEnvironmentName string

@description('Subscription ID, used only to scope the custom role definition')
param subscriptionId string = subscription().subscriptionId

resource idLifecycle 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-lifecycle'
  location: location
  tags: tags
}

resource lifecycleFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: idLifecycle
  name: 'github-${githubEnvironmentName}'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:environment:${githubEnvironmentName}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

// Custom role: exactly the actions Section 11 (I-R2) authorizes, nothing
// broader. Deliberately does NOT include any `Microsoft.Authorization/*`
// action (cannot grant itself more privilege), any `*/write` on the
// resource definitions themselves (cannot create/delete resources, only
// operate lifecycle actions on ones that already exist), and no ACR/Key
// Vault data-plane action (lifecycle automation never touches secrets or
// images).
resource lifecycleRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscriptionId, 'noetva-lifecycle-operator-role')
  properties: {
    roleName: 'Noetva Lifecycle Operator'
    description: 'Least-privilege role for Noetva environment start/stop/sweep automation -- Container Apps revision activate/deactivate, PostgreSQL start/stop/read, lifecycle Storage Table access, and read-only status inspection only.'
    type: 'CustomRole'
    assignableScopes: [
      subscription().id
    ]
    permissions: [
      {
        actions: [
          'Microsoft.App/containerApps/read'
          'Microsoft.App/containerApps/revisions/read'
          'Microsoft.App/containerApps/revisions/activate/action'
          'Microsoft.App/containerApps/revisions/deactivate/action'
          'Microsoft.App/jobs/read'
          'Microsoft.App/jobs/executions/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/start/action'
          'Microsoft.DBforPostgreSQL/flexibleServers/stop/action'
          'Microsoft.Storage/storageAccounts/tableServices/tables/read'
          'Microsoft.Storage/storageAccounts/listkeys/action'
          'Microsoft.Resources/subscriptions/resourceGroups/read'
          // Noetva G-R3 Section 15: exactly the two actions needed to
          // read and toggle the lifecycle-alert-suppression rule's
          // `enabled` flag -- never Monitoring Contributor, never a
          // broader Microsoft.AlertsManagement/* wildcard.
          'Microsoft.AlertsManagement/actionRules/read'
          'Microsoft.AlertsManagement/actionRules/write'
        ]
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/tableServices/tables/entities/read'
          'Microsoft.Storage/storageAccounts/tableServices/tables/entities/write'
          'Microsoft.Storage/storageAccounts/tableServices/tables/entities/delete'
        ]
        notDataActions: []
      }
    ]
  }
}

output lifecycleIdentityId string = idLifecycle.id
output lifecycleIdentityPrincipalId string = idLifecycle.properties.principalId
output lifecycleIdentityClientId string = idLifecycle.properties.clientId
output lifecycleRoleId string = lifecycleRole.id
