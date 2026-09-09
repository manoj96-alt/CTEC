// Assigns the Noetva Lifecycle Operator custom role to the lifecycle
// identity, at whatever resource-group scope this module is deployed into
// (see lifecycle-main.bicep's per-environment `scope:` loop). Kept as its
// own tiny module because role assignment `name` (a guid()) must be
// resolvable from plain parameters, not chained through a cross-scope
// module output inline (the same BCP120 constraint discovered and
// resolved in R1 -- see modules/role-assignments.bicep's own comment
// history).
metadata description = 'Assigns the lifecycle operator role at one resource-group scope'

@description('Principal ID of the lifecycle managed identity')
param principalId string

@description('Full resource ID of the custom role definition to assign')
param roleDefinitionId string

resource assignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, principalId, roleDefinitionId)
  properties: {
    roleDefinitionId: roleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
