"""Repository for OQI3 governed `BusinessRule` persistence (CDD-041 §4,
§24, §26). `activate_new_version` mirrors
`OqiCrossSourceCorrespondenceRepositoryImpl.activate_new_version`'s /
`OqiQualityRuleRepositoryImpl`'s exact retire-then-flush-then-activate
transaction ordering, so the partial unique index
(`uq_business_rules_one_active_per_condition`) is never transiently
violated within the same transaction. `create`/`activate_new_version` run
CDD-041 §26's publication-time tenant-consistency check for every input
binding's `source_field_id` -- joined through `source_fields ->
source_objects`, since `SourceField` carries no `tenant_id` column of its
own (CDD-019 §18) -- before any row is persisted; a cross-tenant or
malformed rule must never become ACTIVE."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi_business_rule.rule import (
    BusinessRule,
    BusinessRuleInputBinding,
    BusinessRulePurpose,
    BusinessRuleStatus,
    ExpectedType,
    OqiMalformedBusinessRuleError,
    RuleFamily,
    ast_from_json,
    ast_to_json,
)
from app.infrastructure.persistence.models.oqi_business_rule import (
    BusinessRuleInputBindingORM,
    BusinessRuleORM,
)
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject


class OqiBusinessRuleRepository(Protocol):
    def create(self, rule: BusinessRule) -> None: ...

    def get_by_id(self, rule_id: UUID) -> BusinessRule | None: ...

    def get_active(self, *, tenant_id: str, business_condition_id: str) -> BusinessRule | None: ...

    def activate_new_version(self, new_rule: BusinessRule, *, retired_on: datetime) -> None: ...


class OqiBusinessRuleRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, rule: BusinessRule) -> None:
        self._validate_tenant_consistency(rule)
        self.session.add(_to_orm(rule))
        self.session.flush()
        for binding in rule.input_bindings:
            self.session.add(
                BusinessRuleInputBindingORM(
                    rule_id=rule.rule_id,
                    input_role=binding.input_role,
                    source_field_id=binding.source_field_id,
                    required=binding.required,
                    expected_type=binding.expected_type.value,
                )
            )
        self.session.flush()

    def get_by_id(self, rule_id: UUID) -> BusinessRule | None:
        model = self.session.get(BusinessRuleORM, rule_id)
        if model is None:
            return None
        return _to_domain(model, self._bindings_of(rule_id))

    def get_active(self, *, tenant_id: str, business_condition_id: str) -> BusinessRule | None:
        model = self.session.execute(
            select(BusinessRuleORM).where(
                BusinessRuleORM.tenant_id == tenant_id,
                BusinessRuleORM.business_condition_id == business_condition_id,
                BusinessRuleORM.status == BusinessRuleStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        return _to_domain(model, self._bindings_of(model.rule_id))

    def activate_new_version(self, new_rule: BusinessRule, *, retired_on: datetime) -> None:
        if new_rule.status is not BusinessRuleStatus.ACTIVE:
            raise ValueError("activate_new_version requires an ACTIVE new_rule")

        current = self.session.execute(
            select(BusinessRuleORM).where(
                BusinessRuleORM.tenant_id == new_rule.tenant_id,
                BusinessRuleORM.business_condition_id == new_rule.business_condition_id,
                BusinessRuleORM.status == BusinessRuleStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if current is not None:
            current.status = BusinessRuleStatus.RETIRED.value
            current.retired_on = retired_on
            self.session.flush()

        self.create(new_rule)
        self.session.flush()

    def _bindings_of(self, rule_id: UUID) -> tuple[BusinessRuleInputBindingORM, ...]:
        rows = (
            self.session.execute(
                select(BusinessRuleInputBindingORM).where(
                    BusinessRuleInputBindingORM.rule_id == rule_id
                )
            )
            .scalars()
            .all()
        )
        return tuple(rows)

    def _validate_tenant_consistency(self, rule: BusinessRule) -> None:
        for binding in rule.input_bindings:
            owning_tenant_id = self.session.execute(
                select(SourceObject.tenant_id)
                .join(
                    SourceFieldORM,
                    SourceFieldORM.source_object_id == SourceObject.source_object_id,
                )
                .where(SourceFieldORM.source_field_id == binding.source_field_id)
            ).scalar_one_or_none()
            if owning_tenant_id is None:
                raise OqiMalformedBusinessRuleError(
                    f"input binding {binding.input_role!r} references an unknown "
                    f"source_field_id: {binding.source_field_id}"
                )
            if owning_tenant_id != rule.tenant_id:
                raise OqiMalformedBusinessRuleError(
                    f"input binding {binding.input_role!r} references a source_field "
                    f"belonging to tenant {owning_tenant_id!r}, not the rule's own "
                    f"tenant {rule.tenant_id!r}"
                )


def _to_orm(rule: BusinessRule) -> BusinessRuleORM:
    return BusinessRuleORM(
        rule_id=rule.rule_id,
        business_condition_id=rule.business_condition_id,
        version=rule.version,
        tenant_id=rule.tenant_id,
        rule_family=rule.rule_family.value,
        applicability=(ast_to_json(rule.applicability) if rule.applicability is not None else None),
        predicate=ast_to_json(rule.predicate),
        status=rule.status.value,
        created_by=rule.created_by,
        created_on=rule.created_on,
        retired_on=rule.retired_on,
        dimension=rule.dimension.value,
    )


def _to_domain(
    model: BusinessRuleORM, binding_models: tuple[BusinessRuleInputBindingORM, ...]
) -> BusinessRule:
    bindings = tuple(
        BusinessRuleInputBinding(
            input_role=binding_model.input_role,
            source_field_id=binding_model.source_field_id,
            required=binding_model.required,
            expected_type=ExpectedType(binding_model.expected_type),
        )
        for binding_model in binding_models
    )
    return BusinessRule(
        rule_id=model.rule_id,
        business_condition_id=model.business_condition_id,
        version=model.version,
        tenant_id=model.tenant_id,
        rule_family=RuleFamily(model.rule_family),
        applicability=(
            ast_from_json(model.applicability) if model.applicability is not None else None
        ),
        predicate=ast_from_json(model.predicate),
        input_bindings=bindings,
        status=BusinessRuleStatus(model.status),
        created_by=model.created_by,
        created_on=model.created_on,
        retired_on=model.retired_on,
        dimension=BusinessRulePurpose(model.dimension),
    )
