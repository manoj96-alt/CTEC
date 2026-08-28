"""Repository for OQI governed `QualityRule` persistence (CDD-039 §18,
§33-§34, §39; OQI1 Artifact Authorization §4). `activate_new_version`
implements CDD-039 §34's exact retire-then-activate transaction ordering:
the currently-ACTIVE row (if any) for the same `quality_condition_id` is
retired and flushed *before* the new version is added, so the partial
unique index (`uq_quality_rules_one_active_per_condition`) is never
transiently violated within the same transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
    ValidityPrimitive,
    validate_rule_shape,
)
from app.infrastructure.persistence.models.oqi_quality_rule import QualityRuleORM


class OqiQualityRuleRepository(Protocol):
    def create(self, rule: QualityRule) -> None: ...

    def get_by_id(self, rule_id: UUID) -> QualityRule | None: ...

    def get_active(self, quality_condition_id: str) -> QualityRule | None: ...

    def activate_new_version(self, new_rule: QualityRule, *, retired_on: datetime) -> None: ...


class OqiQualityRuleRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, rule: QualityRule) -> None:
        # CDD-039 §33 point 2: explicit re-validation before persistence,
        # not merely relying on __post_init__ having already run.
        validate_rule_shape(
            dimension=rule.dimension,
            finding_type=rule.finding_type,
            validity_primitive=rule.validity_primitive,
            rule_parameters=rule.rule_parameters,
        )
        self.session.add(_to_orm(rule))

    def get_by_id(self, rule_id: UUID) -> QualityRule | None:
        model = self.session.get(QualityRuleORM, rule_id)
        return None if model is None else _to_domain(model)

    def get_active(self, quality_condition_id: str) -> QualityRule | None:
        model = self.session.execute(
            select(QualityRuleORM).where(
                QualityRuleORM.quality_condition_id == quality_condition_id,
                QualityRuleORM.status == QualityRuleStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        return None if model is None else _to_domain(model)

    def activate_new_version(self, new_rule: QualityRule, *, retired_on: datetime) -> None:
        # CDD-039 §33 point 2.
        validate_rule_shape(
            dimension=new_rule.dimension,
            finding_type=new_rule.finding_type,
            validity_primitive=new_rule.validity_primitive,
            rule_parameters=new_rule.rule_parameters,
        )
        if new_rule.status is not QualityRuleStatus.ACTIVE:
            raise ValueError("activate_new_version requires an ACTIVE new_rule")

        # CDD-039 §34: retire the current ACTIVE row (if any) and flush it
        # before adding the new ACTIVE row, so the two statements never
        # both claim ACTIVE for this condition simultaneously.
        current = self.session.execute(
            select(QualityRuleORM).where(
                QualityRuleORM.quality_condition_id == new_rule.quality_condition_id,
                QualityRuleORM.status == QualityRuleStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if current is not None:
            current.status = QualityRuleStatus.RETIRED.value
            current.retired_on = retired_on
            self.session.flush()

        self.session.add(_to_orm(new_rule))
        self.session.flush()


def _to_orm(rule: QualityRule) -> QualityRuleORM:
    return QualityRuleORM(
        rule_id=rule.rule_id,
        quality_condition_id=rule.quality_condition_id,
        version=rule.version,
        dimension=rule.dimension.value,
        finding_type=rule.finding_type.value,
        validity_primitive=(
            None if rule.validity_primitive is None else rule.validity_primitive.value
        ),
        information_element_requirement_id=rule.information_element_requirement_id,
        rule_parameters=dict(rule.rule_parameters),
        status=rule.status.value,
        created_by=rule.created_by,
        created_on=rule.created_on,
        retired_on=rule.retired_on,
    )


def _to_domain(model: QualityRuleORM) -> QualityRule:
    rule_parameters: dict[str, Any] = dict(model.rule_parameters)
    return QualityRule(
        rule_id=model.rule_id,
        quality_condition_id=model.quality_condition_id,
        version=model.version,
        dimension=QualityDimension(model.dimension),
        finding_type=QualityFindingType(model.finding_type),
        validity_primitive=(
            None
            if model.validity_primitive is None
            else ValidityPrimitive(model.validity_primitive)
        ),
        information_element_requirement_id=model.information_element_requirement_id,
        rule_parameters=rule_parameters,
        status=QualityRuleStatus(model.status),
        created_by=model.created_by,
        created_on=model.created_on,
        retired_on=model.retired_on,
    )
