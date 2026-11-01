"""SupplyChain IQ - Decision Workflow & Idempotency Service."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ForbiddenError, IdempotencyConflictError
from backend.app.core.idempotency import idempotency_store
from backend.app.core.rbac import Permission, UserRole, has_permission
from backend.app.repositories.decision_repo import DecisionRepository
from backend.app.schemas.decision_api import DecisionSubmitRequest, DecisionSubmitResponse


class DecisionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DecisionRepository(session)

    async def submit_decision(
        self,
        request: DecisionSubmitRequest,
        user_id: str,
        user_role: UserRole,
        idempotency_key: Optional[str] = None,
    ) -> DecisionSubmitResponse:
        # 1. Check RBAC permissions
        required_perm = Permission.MITIGATION_APPROVE if request.decision.value == "APPROVED" else Permission.MITIGATION_REJECT
        if not has_permission(user_role, required_perm):
            raise ForbiddenError(f"Role '{user_role.value}' is not authorized to submit {request.decision.value} decisions.")

        # 2. Check Idempotency Key
        if idempotency_key:
            is_new, record = idempotency_store.start_operation(idempotency_key)
            if not is_new:
                if record.status == "IN_PROGRESS":
                    raise IdempotencyConflictError(idempotency_key)
                if record.status == "COMPLETED" and record.response_body:
                    # Return cached response idempotently
                    return DecisionSubmitResponse(**record.response_body)

        try:
            # 3. Transactional decision submission
            decision = await self.repo.submit_decision(
                request=request,
                planner_id=user_id,
                user_role=user_role.value,
            )

            dec_val = decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision)
            resp = DecisionSubmitResponse(
                id=decision.id,
                business_id=decision.business_id,
                mitigation_option_id=decision.mitigation_option_id,
                planner_id=decision.planner_id,
                decision=dec_val,
                override_qty=decision.override_qty,
                reason=decision.reason,
                decided_at=decision.decided_at,
                status="SUCCESS",
                message=f"Decision {dec_val} registered successfully.",
            )

            # 4. Cache idempotency outcome
            if idempotency_key:
                idempotency_store.complete_operation(idempotency_key, 201, resp.model_dump(mode="json"))

            return resp

        except Exception as exc:
            if idempotency_key:
                idempotency_store.release_operation(idempotency_key)
            raise exc
