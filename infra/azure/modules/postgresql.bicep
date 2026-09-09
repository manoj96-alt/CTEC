// Azure Database for PostgreSQL Flexible Server, version 17 -- confirmed
// GA-supported directly against current Microsoft documentation during
// Noetva D0 (Section H). Private access only via the delegated subnet +
// private DNS zone from network.bicep; no public network access, exactly
// preserving today's Docker Compose topology where Postgres has no
// published host port at all.
metadata description = 'PostgreSQL Flexible Server for Noetva'

@description('Naming prefix, e.g. noetva-prod-eus2')
param namePrefix string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Delegated subnet ID for Postgres private access')
param delegatedSubnetId string

@description('Private DNS zone ID for Postgres private access')
param privateDnsZoneId string

@description('Compute SKU, e.g. Standard_B2s (Burstable, dev), Standard_D2ds_v5 (General Purpose, staging/prod)')
param skuName string = 'Standard_B2s'

@description('SKU tier: Burstable | GeneralPurpose | MemoryOptimized')
param skuTier string = 'Burstable'

@description('Storage size in GiB')
param storageSizeGb int = 32

@description('Backup retention in days (Noetva D0 Section AF: 14 initial, unless evidence requires otherwise)')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 14

@description('High-availability mode: Disabled | ZoneRedundant (Noetva D0 Section AR/AJ: ZoneRedundant for production, Disabled acceptable for dev/staging)')
param highAvailabilityMode string = 'Disabled'

@description('PostgreSQL administrator login name (break-glass ADMIN authority only -- never the application or migration role, Noetva I0-R1 Section 20)')
param administratorLogin string = 'noetva_pg_admin'

@secure()
@description('PostgreSQL administrator password. Supplied at deployment time from Key Vault by the deployment pipeline -- never committed, never a Bicep default (Noetva I0-R1 Section 11).')
param administratorPassword string

resource flexibleServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${namePrefix}-pg'
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: '17'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    network: {
      delegatedSubnetResourceId: delegatedSubnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
      publicNetworkAccess: 'Disabled'
    }
    storage: {
      storageSizeGB: storageSizeGb
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: highAvailabilityMode
    }
  }
}

resource enforceSsl 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: flexibleServer
  name: 'require_secure_transport'
  properties: {
    value: 'on'
    source: 'user-override'
  }
}

// Required for migration 0001 (canonical_v1_3.sql)'s `gen_random_uuid()`
// column defaults, used across virtually every table -- confirmed by
// actually running the 46-migration chain against a real PostgreSQL 17
// container, which failed until pgcrypto was both allow-listed here AND
// created via db-bootstrap/001_create_roles_and_grants.sql (Noetva I0-R1
// Section 19/24). Azure Database for PostgreSQL Flexible Server requires
// this allow-list step before ANY role -- including the administrator
// login -- can successfully `CREATE EXTENSION` it (independently confirmed
// against current Microsoft documentation, "Allow Extensions in Azure
// Database for PostgreSQL Flexible Server").
resource allowlistExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: flexibleServer
  name: 'azure.extensions'
  properties: {
    value: 'pgcrypto'
    source: 'user-override'
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: flexibleServer
  name: 'ctec'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output serverId string = flexibleServer.id
output serverName string = flexibleServer.name
output serverFqdn string = flexibleServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
