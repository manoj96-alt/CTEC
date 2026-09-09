// Deliberately small initial alert set (Noetva D0 Section AE / I0-R1
// Section 35 -- avoid alert-catalog sprawl). Split from the workspace
// (monitoring-workspace-only.bicep) because these alerts scope to
// resources (PostgreSQL, the migration Job) that must already exist.
//
// NOTE (disclosed, not hidden): the exact metric names/dimensions below
// (`storage_percent`, `active_connections`, `JobExecutionCount` +
// `executionStatus`) are written from current knowledge of the
// PostgreSQL Flexible Server and Container Apps Jobs metric namespaces but
// were NOT independently re-verified against `az monitor metrics
// list-definitions` against a real deployed resource in this phase (no
// Azure resource exists yet to query). This is flagged as a residual risk
// (see infra/azure/README.md) to confirm at first real deployment; Bicep's
// own compiler does not validate that a metric name string is real, only
// ARM does, at deployment time.
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
          metricName: 'JobExecutionCount'
          dimensions: [
            {
              name: 'executionStatus'
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
