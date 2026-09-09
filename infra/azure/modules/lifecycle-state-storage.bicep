// Durable lifecycle state, deliberately NOT in PostgreSQL (Noetva G-R2
// Section 16 / I-R2 Section 9): the controller must be able to know
// "DATABASE IS STOPPED" while PostgreSQL itself is unreachable. One Storage
// Account + one Table, shared across this subscription's non-production
// environments (negligible cost, one row per environment — see
// lifecycle_controller.py's LifecycleRow for the exact schema). Table
// entity ETags provide optimistic-concurrency layer 2 (GitHub Actions
// `concurrency:` groups are layer 1, applied in the workflow YAML, not
// here).
metadata description = 'Lifecycle state Storage Table for Noetva environment automation'

@description('Naming prefix, e.g. noetva-lifecycle-eus2 (storage account names must be globally unique, lowercase alphanumeric only)')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Log Analytics workspace resource ID for diagnostic settings')
param logAnalyticsWorkspaceId string

// The linter's BCP334 (min-length-3) warning on this line is a known,
// harmless false positive: the literal prefix "noetva" + suffix "lcst" is
// always >= 10 characters regardless of `namePrefix`'s content, but
// Bicep's static analysis cannot prove that through a replace()/take()
// chain. Accepted and documented, not fixable, matching R1's own
// precedent of one accepted, explained compiler warning.
var storageAccountName = take(replace('noetva${namePrefix}lcst', '-', ''), 24)

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    accessTier: 'Hot'
  }
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource lifecycleTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-01-01' = {
  parent: tableService
  name: 'noetvalifecyclestate'
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: storageAccount
  name: 'diag-to-log-analytics'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      {
        category: 'Transaction'
        enabled: true
      }
    ]
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output tableName string = lifecycleTable.name
output tableEndpoint string = storageAccount.properties.primaryEndpoints.table
