// One Key Vault per environment (Noetva D0 Section W). RBAC authorization
// (never legacy access policies), soft delete always on, purge protection
// on for production, diagnostic logging to Log Analytics. Secret values are
// never set here -- see infra/azure/README.md's manual-input register;
// this module only creates the vault and its placeholder secret objects
// (names only) that the operator populates out-of-band via `az keyvault
// secret set`, never via source control.
metadata description = 'Key Vault for Noetva secrets, RBAC-authorized'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Enable purge protection. Required for production; optional for dev/staging.')
param enablePurgeProtection bool = false

@description('Log Analytics workspace resource ID for diagnostic settings')
param logAnalyticsWorkspaceId string

@description('Azure AD tenant ID for the vault')
param tenantId string = subscription().tenantId

var vaultName = '${namePrefix}-kv'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: enablePurgeProtection ? true : null
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: keyVault
  name: 'diag-to-log-analytics'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// Deliberately: this module creates ONLY the vault, never any secret
// VALUE. Secret objects are intentionally NOT declared as Bicep resources
// here -- doing so would make every redeploy an idempotent no-op that
// silently resets whatever real value an operator had set via `az keyvault
// secret set`, a genuine footgun. The required secret NAMES this
// environment expects are documented in infra/azure/README.md's manual-
// input register and created out-of-band, once, by an operator with
// Key Vault Secrets Officer access -- never by this template, never
// committed to git (Noetva I0-R1 Section 11).
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
