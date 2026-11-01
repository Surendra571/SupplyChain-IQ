"""SupplyChain IQ - Mitigation Decision Repository & Transaction Manager."""

from datetime import datetime, timezone
import json
from typing import Optional, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import BusinessRuleViolationError, ConflictError, EntityNotFoundError
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import (
    ALLOWED_MITIGATION_TRANSITIONS,
    ALLOWED_SHORTAGE_TRANSITIONS,
    MitigationDecisionType,
    MitigationOptionStatus,
    ShortageStatus,
    validate_transition,
)
from backend.app.models.planning import MitigationDecision, MitigationOption, Shortage
from backend.app.schemas.decision_api import DecisionSubmitRequest


class DecisionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_decision_by_id(self, identifier: str) -> Optional[MitigationDecision]:
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = select(MitigationDecision).where(MitigationDecision.id == val_uuid)
        except ValueError:
            stmt = select(MitigationDecision).where(MitigationDecision.business_id == identifier)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def submit_decision(
        self,
        request: DecisionSubmitRequest,
        planner_id: str,
        user_role: str,
    ) -> MitigationDecision:
        """Execute transactional planner approval/rejection with state validation and immutable audit event."""
        # 1. Fetch target MitigationOption
        opt_identifier = request.mitigation_option_id
        try:
            val_uuid = uuid.UUID(opt_identifier)
            opt_stmt = select(MitigationOption).where(MitigationOption.id == val_uuid)
        except ValueError:
            opt_stmt = select(MitigationOption).where(MitigationOption.business_id == opt_identifier)

        opt_res = await self.session.execute(opt_stmt)
        option = opt_res.scalar_one_or_none()
        if not option:
            raise EntityNotFoundError("MitigationOption", opt_identifier)

        # 2. Fetch associated Shortage
        shortage_stmt = select(Shortage).where(Shortage.id == option.shortage_id)
        shortage_res = await self.session.execute(shortage_stmt)
        shortage = shortage_res.scalar_one_or_none()
        if not shortage:
            raise EntityNotFoundError("Shortage", str(option.shortage_id))

        # 3. Validate state transitions
        target_opt_status = (
            MitigationOptionStatus.APPROVED
            if request.decision in (MitigationDecisionType.APPROVED, MitigationDecisionType.OVERRIDDEN)
            else MitigationOptionStatus.REJECTED
        )

        current_opt_status = option.status
        if not validate_transition(current_opt_status, target_opt_status, ALLOWED_MITIGATION_TRANSITIONS):
            raise BusinessRuleViolationError(
                f"Cannot transition mitigation option from {current_opt_status.value} to {target_opt_status.value}."
            )

        # Shortage target status
        target_shortage_status = (
            ShortageStatus.MITIGATED
            if request.decision in (MitigationDecisionType.APPROVED, MitigationDecisionType.OVERRIDDEN)
            else ShortageStatus.ACKNOWLEDGED
        )

        opt_status_str = option.status.value if hasattr(option.status, "value") else str(option.status)
        shortage_status_str = shortage.status.value if hasattr(shortage.status, "value") else str(shortage.status)
        decision_str = request.decision.value if hasattr(request.decision, "value") else str(request.decision)

        before_state = {
            "option_status": opt_status_str,
            "shortage_status": shortage_status_str,
            "recommended_qty": option.recommended_qty,
        }

        # 4. Create Decision Record
        decision_record = MitigationDecision(
            business_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
            mitigation_option_id=option.id,
            planner_id=planner_id,
            decision=request.decision,
            override_qty=request.override_qty,
            reason=request.reason,
            decided_at=datetime.now(timezone.utc),
        )
        self.session.add(decision_record)

        # 5. Mutate statuses
        option.status = target_opt_status
        shortage.status = target_shortage_status

        target_opt_str = target_opt_status.value if hasattr(target_opt_status, "value") else str(target_opt_status)
        target_shortage_str = target_shortage_status.value if hasattr(target_shortage_status, "value") else str(target_shortage_status)

        after_state = {
            "option_status": target_opt_str,
            "shortage_status": target_shortage_str,
            "decision": decision_str,
            "override_qty": request.override_qty,
            "reason": request.reason,
            "planner_id": planner_id,
        }

        # 6. Create Immutable Audit Event
        audit = AuditEvent(
            business_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            entity_name="MitigationDecision",
            entity_id=decision_record.business_id,
            action=decision_str,
            performed_by=f"{planner_id} ({user_role})",
            before_state_json=json.dumps(before_state),
            after_state_json=json.dumps(after_state),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)

        # 7. Commit transaction
        await self.session.commit()
        await self.session.refresh(decision_record)

        return decision_record
