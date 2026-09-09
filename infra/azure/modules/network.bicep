// Network foundation: VNet with a delegated subnet for the Container Apps
// Environment and a delegated subnet for PostgreSQL Flexible Server private
// access, plus (staging/production only) a NAT Gateway giving connector
// egress a stable, allowlistable IP (Noetva D0 Section R; I0-R1 Section 17).
// No Front Door, no Application Gateway, no Azure Firewall, no
// HTTP_PROXY/HTTPS_PROXY of any kind (D0 Section S/R -- the connector does
// not honor an application-layer proxy by design and none is introduced here).
metadata description = 'VNet, subnets, private DNS, and NAT egress for Noetva'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Address space for the VNet')
param vnetAddressPrefix string = '10.20.0.0/16'

@description('Address prefix for the Container Apps environment infrastructure subnet')
param containerAppsSubnetPrefix string = '10.20.0.0/23'

@description('Address prefix for the PostgreSQL Flexible Server delegated subnet')
param postgresSubnetPrefix string = '10.20.2.0/24'

@description('Whether to provision a NAT Gateway with a static public IP for deterministic outbound egress. Required for staging/production; DEV may omit it to reduce cost (Noetva D0 Section R / I0-R1 Section 17).')
param enableNatGateway bool = true

var natPublicIpName = '${namePrefix}-pip-nat'
var natGatewayName = '${namePrefix}-nat'

resource natPublicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = if (enableNatGateway) {
  name: natPublicIpName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource natGateway 'Microsoft.Network/natGateways@2023-11-01' = if (enableNatGateway) {
  name: natGatewayName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIpAddresses: [
      {
        id: natPublicIp.id
      }
    ]
    idleTimeoutInMinutes: 10
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${namePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          natGateway: enableNatGateway ? {
            id: natGateway.id
          } : null
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          delegations: [
            {
              name: 'Microsoft.DBforPostgreSQL.flexibleServers'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

resource postgresPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: '${namePrefix}.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource postgresPrivateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresPrivateDnsZone
  name: '${namePrefix}-pg-dns-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output vnetId string = vnet.id
output containerAppsSubnetId string = vnet.properties.subnets[0].id
output postgresSubnetId string = vnet.properties.subnets[1].id
output postgresPrivateDnsZoneId string = postgresPrivateDnsZone.id
output natGatewayEgressIp string = natPublicIp.?properties.?ipAddress ?? ''
output natEnabled bool = enableNatGateway
