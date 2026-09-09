// Lifecycle-aware alert suppression (Noetva G-R3 Section 10/11, required
// before DEMO, not before DEV). Verified real Azure Monitor capability
// (Microsoft Learn, "Alert processing rules for Azure Monitor alerts",
// resource type `Microsoft.AlertsManagement/actionRules`), not the
// fabricated "Action Rule with a Storage Table lookup condition" a prior
// phase merely speculated about -- no such condition type exists. The
// REAL mechanism: a `Suppression`-type alert processing rule, always
// active by structure, whose own `Enabled`/`Disabled` status is toggled
// by the lifecycle start/stop workflows themselves (Option A from G-R3
// Section 11) via `az monitor alert-processing-rule update --enabled`.
//
// Scope is deliberately narrow: this rule's `conditions` filter matches
// ONLY `monitorService = Platform` alerts on `Microsoft.App/containerApps`
// resource types within this one environment's resource group --  it
// structurally cannot match PostgreSQL storage/connection alerts, the
// migration-Job-failure alert, Key Vault/security signals, or budget/cost
// alerts, which live on different resource types entirely and are never
// suppressed by this rule (Noetva G-R3 Section 12's truth contract).
//
// DISCLOSED LIMITATION, not hidden: Microsoft's own documentation states
// "After you create or update an alert processing rule, it can take up to
// 30 minutes for the rule to take effect." The stop/start sequencing
// (Section 14) accounts for this as a known propagation delay, not an
// instantaneous switch.
metadata description = 'Lifecycle-aware alert-suppression processing rule for one environment'

@description('Naming prefix, e.g. noetva-demo-eus2')
param namePrefix string

@description('Resource tags')
param tags object

@description('Whether the suppression rule starts enabled or disabled. The lifecycle stop/start workflows toggle this boolean at runtime via `az monitor alert-processing-rule update --enabled`; the initial deploy-time value only matters for the very first Bicep apply.')
param initialEnabled bool = false

resource suppressionRule 'Microsoft.AlertsManagement/actionRules@2021-08-08' = {
  name: '${namePrefix}-availability-suppression'
  location: 'Global'
  tags: tags
  properties: {
    scopes: [
      resourceGroup().id
    ]
    // Real ARM schema (confirmed directly by Bicep's own bundled type
    // definitions, not guessed): `conditions` is an array of field-level
    // filters, ANDed together -- deliberately narrow, matching ONLY
    // Container Apps platform-metric alerts within this resource group,
    // never Postgres/Key Vault/security/budget alerts (Noetva G-R3
    // Section 12).
    conditions: [
      {
        field: 'MonitorService'
        operator: 'Equals'
        values: [
          'Platform'
        ]
      }
      {
        field: 'TargetResourceType'
        operator: 'Contains'
        values: [
          'MICROSOFT.APP/CONTAINERAPPS'
        ]
      }
    ]
    // `Suppression` is the action type, confirmed correct terminology
    // from Microsoft's own documentation ("Suppression: This action
    // removes all the action groups from the affected fired alerts").
    actions: [
      {
        actionType: 'RemoveAllActionGroups'
      }
    ]
    enabled: initialEnabled
    description: 'Suppresses Container Apps platform-metric alert notifications while this environment is intentionally governed-dormant. Toggled by the lifecycle start/stop workflows, never by manual portal action (Noetva G-R3 Section 11).'
  }
}

output suppressionRuleId string = suppressionRule.id
output suppressionRuleName string = suppressionRule.name
