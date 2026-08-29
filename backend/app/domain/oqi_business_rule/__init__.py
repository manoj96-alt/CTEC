"""OQI3 Business-Rule Quality Intelligence domain package (CDD-041).

Governed, deterministic evaluation of business expectations (`BusinessRule`)
over governed `FieldValueEvidence` for a single-record subject. `BusinessRule`
is a first-class sibling of OQI1's `QualityRule` -- never an extension,
subtype, or shared-table discriminator. This package (OQI3-I1) provides only
the governed rule/binding/AST foundation and publication-time validation;
no evaluation runtime, no Finding lifecycle (OQI3-I2/I3)."""

from __future__ import annotations
