// One Container Apps (Managed) Environment, VNet-integrated into the
// dedicated delegated subnet from network.bicep (Noetva D0 Section N).
metadata description = 'Container Apps Environment for Noetva'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Delegated subnet ID for the Container Apps Environment infrastructure')
param infrastructureSubnetId string

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Log Analytics workspace customer ID (GUID), required by the Container Apps Environment log configuration')
param logAnalyticsCustomerId string

@secure()
@description('Log Analytics shared key, required by the Container Apps Environment log configuration')
param logAnalyticsSharedKey string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    zoneRedundant: false
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: environment
  name: 'diag-to-log-analytics'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
  }
}

output environmentId string = environment.id
output environmentDefaultDomain string = environment.properties.defaultDomain
