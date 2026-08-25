"""Internal Gate U -- Ephemeral Governed What-if Simulation application
service (CDD-032 §6-§9; Gate U Artifact Authorization §6). For a
caller-supplied hypothetical `InformationElementEvidenceFitnessResult`,
computes what Gate T's own frozen, unmodified
`SourceEvidenceFitnessImpactRemediationApplicationService.derive(...)`
would report -- an ephemeral, non-authoritative simulation, never derived
from, and never written to, real evidence, mapping, decision, or ontology
state. Performs no I/O of any kind: a pure function over two already-in-
memory objects (a hypothetical fitness result and the same `Blueprint` the
caller already retrieved). Constructs `SourceEvidenceFitnessImpactRemediationApplicationService`
directly, with no constructor injection -- it declares no `__init__` of its
own and has no I/O to substitute (Gate U Artifact Authorization §6)."""

from dataclasses import dataclass

from app.application.source_evidence_fitness_evaluation import (
    InformationElementEvidenceFitnessResult,
)
from app.application.source_evidence_fitness_impact_remediation import (
    EvidenceFitnessImpactContext,
    SourceEvidenceFitnessImpactRemediationApplicationService,
)
from app.domain.blueprint import Blueprint


@dataclass(frozen=True, slots=True)
class WhatIfSimulationResult:
    simulated_impact_context: EvidenceFitnessImpactContext


class WhatIfSimulationApplicationService:
    def simulate(
        self,
        *,
        hypothetical_fitness_result: InformationElementEvidenceFitnessResult,
        blueprint: Blueprint,
    ) -> WhatIfSimulationResult:
        results = SourceEvidenceFitnessImpactRemediationApplicationService().derive(
            fitness_results=(hypothetical_fitness_result,), blueprint=blueprint
        )
        return WhatIfSimulationResult(simulated_impact_context=results[0])
