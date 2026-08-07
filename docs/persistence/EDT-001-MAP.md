# EDT-001-MAP — Version 3 Ingestion-to-Canonical Contract

Version: 1.0  
Status: Frozen for CDD-002 source-provenance loading  
Dataset: EDT-001-V3

## Boundary

EDT-001 CSV rows are external source records. CDD-002 persists provenance only. It does not perform identity resolution, semantic resolution, assertion construction, relationship construction, or knowledge institutionalization.

## Common mapping

Every CSV row maps to one canonical `Source Object`:

| CSV input | Canonical entity | Canonical attributes | Rule |
| --- | --- | --- | --- |
| Filename and complete row | Source Object | `source_object_id` | UUIDv5 of seed namespace, filename, and canonical row serialization |
| Filename and complete row | Source Object | `source_object_name` | `EDT-001-V3:<filename>:<row-digest>` |
| Dataset version | Source Object | `source_system_id` | FK to deterministic `EDT-001-V3` Source System |
| ARCH-004 | Source Object | Lifecycle, governance, audit, version attributes | Frozen bootstrap constants and EAD-defined defaults |

The original CSV values remain in the immutable EDT-001 archive. The current Source Object entity has no approved payload attribute, so persistence does not invent one.

## File-specific mappings

| CSV | Additional canonical mapping in CDD-002 | Deferred interpretation |
| --- | --- | --- |
| `SourceSystems.csv` | `SourceSystem` → Source System `source_system_name` | System category semantics |
| `Assertions.csv` | Source Object only | Candidate Assertion validation and construction |
| `Evidence.csv` | Source Object only | Evidence identity and Assertion substantiation |
| `Knowledge.csv` | Source Object only | Knowledge institutionalization |
| `Decisions.csv` | Source Object only | Decision construction and authorization |
| `Experience.csv` | Source Object only | Experience construction |
| `Outcomes.csv` | Source Object only | Outcome linkage |
| `Enterprises.csv` | Source Object only | Enterprise identity and classification |
| `Suppliers.csv` | Source Object only | Enterprise Entity identity, Country, risk, and standing |
| `Materials.csv` | Source Object only | Material entity identity |
| `Products.csv` | Source Object only | Product entity identity |
| `Factories.csv` | Source Object only | Factory entity identity |
| `BOM.csv` | Source Object only | Product-material Institutional Relationships |
| `SupplierMaterial.csv` | Source Object only | Supplier-material Institutional Relationships |
| `PurchaseOrders.csv` | Source Object only | Transactional entity and relationships |
| `Shipments.csv` | Source Object only | Shipment entity and purchase-order relationship |
| `RiskEvents.csv` | Source Object only | Risk semantics and supplier relationship |
| `IdentityConflicts.csv` | Source Object only | Identity Resolution |
| `DemoQuestions.csv` | Source Object only | Decision objective or query interpretation |

## Candidate assertion rule

Rows that appear to describe assertions remain Source Objects until the Assertion Service validates and transforms them. No text parsing or governed predicate selection occurs in CDD-002.

## Idempotency contract

Canonical row serialization sorts field names and preserves source values. Duplicate identical rows resolve to one stable Source Object identifier. File ordering and archive entry ordering do not change identifiers or counts.

