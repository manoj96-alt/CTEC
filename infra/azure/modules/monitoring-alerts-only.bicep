// Deliberately small initial alert set (Noetva D0 Section AE / I0-R1
// Section 35 -- avoid alert-catalog sprawl). Split from the workspace
// (monitoring-workspace-only.bicep) because these alerts scope to
// resources (PostgreSQL, the migration Job) that must already exist.
//
// NOTE (CDD-069): all metric names/dimensions below are now real-Azure
// verified, not merely written from documentation knowledge. `storage_percent`
// (PostgreSQL) and `active_connections` (PostgreSQL) were proven correct by
// the real AZURE-DEV-APPLICATION-TIER-R7-EXECUTION deployment, which created
// both of those alerts successfully. The migration Job alert originally used
// `JobExecutionCount` + `executionStatus`, neither of which exists on
// `Microsoft.App/jobs` -- that real deployment failed on exactly this
// resource with `BadRequest: Couldn't find a metric named JobExecutionCount`.
// CDD-069 (docs/cdd/CDD-069-Azure-DEV-Migration-Job-Monitoring-Correction.md)
// queried the real deployed resource's own metric definitions
// (`az monitor metrics list-definitions`) and corrected it to the real
// metric `Executions` with dimension `state` (values `Running | Processing |
// Stopped | Degraded | Failed | Unknown | Succeeded`, independently
// confirmed against Microsoft's published `JobExecutionRunningState` REST
// API enum) -- see CDD-069 SS4/SS7/SS8 for full evidence and semantics.
metadata description = 'Initial alert set for Noetva'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Resource tags')
param tags object

@description('Action group email recipient for alerts')
param alertEmail string

@description('PostgreSQL Flexible Server resource ID')
param postgresServerId string

@description('Migration Container Apps Job resource ID')
param migrationJobId string

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${namePrefix}-ag-oncall'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'noetvaOncall'
    enabled: true
    emailReceivers: [
      {
        name: 'oncall-email'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

resource pgStorageAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-pg-storage'
  location: 'global'
  tags: tags
  properties: {
    severity: 1
    enabled: true
    scopes: [
      postgresServerId
    ]
    evaluationFrequency: 'PT15M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'storage-over-80-percent'
          metricName: 'storage_percent'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource pgConnectionsAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-pg-connections'
  location: 'global'
  tags: tags
  properties: {
    severity: 2
    enabled: true
    scopes: [
      postgresServerId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'active-connections-high'
          metricName: 'active_connections'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource migrationJobFailureAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${namePrefix}-alert-migration-job-failed'
  location: 'global'
  tags: tags
  properties: {
    severity: 0
    enabled: true
    scopes: [
      migrationJobId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'job-execution-failed'
          metricName: 'Executions'
          dimensions: [
            {
              name: 'state'
              operator: 'Include'
              values: [
                'Failed'
              ]
            }
          ]
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

output actionGroupId string = actionGroup.id
