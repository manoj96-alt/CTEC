// Cost Management budget for one environment's resource group (Noetva
// G-R2 Section AD / I-R2 Section 28). `monthlyAmount` and `contactEmail`
// have NO default -- both are required parameters the operator MUST
// supply at deploy time, because no real Azure pricing evidence exists yet
// to justify inventing a number (Noetva G-R2's own explicit prohibition).
// This module can compile and be reviewed without ever being deployed;
// deployment itself requires the operator to make an actual decision.
metadata description = 'Cost Management budget for one Noetva environment, amount supplied by the operator'

@description('Budget name, e.g. noetva-demo-eus2-budget')
param name string

@description('Monthly budget amount in USD. REQUIRED, no default -- must be supplied by the operator; never fabricated in this template (Noetva G-R2 Section 30).')
@minValue(1)
param monthlyAmount int

@description('Email address to notify. REQUIRED, no default -- never hardcode a personal email into IaC (Noetva G-R2 Section 31).')
param contactEmail string

@description('Resource group name this budget scopes to')
param resourceGroupName string = resourceGroup().name

@description('Budget start date, defaults to the first of the current month. `utcNow()` is only valid as a parameter default in Bicep, hence this indirection.')
param startDate string = utcNow('yyyy-MM-01')

var thresholds = [50, 75, 90, 100]

resource costBudget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: monthlyAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    filter: {
      dimensions: {
        name: 'ResourceGroupName'
        operator: 'In'
        values: [
          resourceGroupName
        ]
      }
    }
    notifications: toObject(thresholds, t => 'threshold-${t}', t => {
      enabled: true
      operator: 'GreaterThanOrEqualTo'
      threshold: t
      thresholdType: 'Actual'
      contactEmails: [
        contactEmail
      ]
    })
  }
}

// Forecast-based notification, layered on top of the four actual-spend
// thresholds (Noetva G-R2 Section AD: "forecast thresholds" evaluated
// alongside percentage thresholds, not instead of them).
resource forecastNotification 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: '${name}-forecast'
  properties: {
    category: 'Cost'
    amount: monthlyAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    filter: {
      dimensions: {
        name: 'ResourceGroupName'
        operator: 'In'
        values: [
          resourceGroupName
        ]
      }
    }
    notifications: {
      'forecast-100': {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: [
          contactEmail
        ]
      }
    }
  }
}

output budgetId string = costBudget.id
