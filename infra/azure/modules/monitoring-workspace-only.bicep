// Log Analytics workspace only. Split from the alert definitions
// (monitoring-alerts-only.bicep) because every other resource's diagnostic
// settings need this workspace's ID/keys BEFORE the resources the alerts
// depend on (PostgreSQL, the migration Job) exist -- a genuine deployment-
// order dependency, not an arbitrary file split.
metadata description = 'Log Analytics workspace for Noetva'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Log retention in days')
@minValue(30)
@maxValue(730)
param logRetentionDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-log'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: logRetentionDays
  }
}

output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
output logAnalyticsCustomerId string = logAnalytics.properties.customerId
// This output carries the workspace's own shared key -- required by the
// Container Apps Environment's log configuration, resolved by ARM only at
// deploy time, never persisted to git. The linter's generic
// outputs-should-not-contain-secrets rule flags this pattern; it is a
// documented, deliberate exception (Microsoft's own Container Apps Bicep
// samples use the identical pattern), not an oversight.
output logAnalyticsSharedKey string = logAnalytics.listKeys().primarySharedKey
