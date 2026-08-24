from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import uuid
import razorpay


load_dotenv("backend/.env")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


app = FastAPI(
    title="AI Financial Decision & Verification Layer",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


decision_records = {}


def get_or_create_record(event_id: str):
    if event_id not in decision_records:
        decision_records[event_id] = {
            "event_id": event_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "event": None,
            "evidence": None,
            "decision": None,
            "policy": None,
            "execution": None,
            "verification": None,
        }

    return decision_records[event_id]


class FinancialEvent(BaseModel):
    payment_id: str
    amount: float = Field(gt=0)
    status: str
    failure_reason: str | None = None
    previous_attempts: int = Field(default=0, ge=0)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "razorpay_configured": bool(
            RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
        ),
    }


@app.post("/financial-events")
def create_financial_event(event: FinancialEvent):

    event_id = f"evt_{uuid.uuid4().hex[:8]}"

    record = get_or_create_record(event_id)

    record["event"] = event.model_dump()

    return {
        "event_id": event_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": "received",
        "event": event.model_dump(),
    }


@app.post("/financial-events/{event_id}/evidence")
def collect_evidence(
    event_id: str,
    event: FinancialEvent,
):

    max_retries = 2
    amount_limit = 10000

    evidence = {
        "event_id": event_id,

        "payment": {
            "payment_id": event.payment_id,
            "amount": event.amount,
            "status": event.status,
            "failure_reason": event.failure_reason,
            "previous_attempts": event.previous_attempts,
        },

        "policy_context": {
            "maximum_retries": max_retries,
            "current_attempts": event.previous_attempts,
            "amount_limit": amount_limit,
            "amount_within_limit": event.amount <= amount_limit,
        },
    }

    record = get_or_create_record(event_id)

    record["evidence"] = evidence

    return {
        "status": "evidence_collected",
        "evidence": evidence,
    }


@app.post("/financial-events/{event_id}/decision")
def make_decision(
    event_id: str,
    event: FinancialEvent,
):

    if event.status == "captured":

        decision = {
            "root_cause": "payment_already_captured",
            "recommended_action": "no_action",
            "reason": (
                "The Razorpay payment is already captured. "
                "No recovery action is required."
            ),
            "source": "development_ai_stub",
        }

    elif event.failure_reason == "authentication_required":

        decision = {
            "root_cause": "authentication_required",
            "recommended_action": "request_authentication",
            "reason": (
                "The payment requires additional authentication "
                "and no previous attempt has been made."
            ),
            "source": "development_ai_stub",
        }

    else:

        decision = {
            "root_cause": "unknown",
            "recommended_action": "escalate",
            "reason": (
                "Insufficient evidence to determine "
                "the root cause."
            ),
            "source": "development_ai_stub",
        }

    record = get_or_create_record(event_id)

    record["decision"] = decision

    return {
        "status": "decision_created",
        "event_id": event_id,
        "decision": decision,
    }


@app.post("/financial-events/{event_id}/policy-check")
def check_policy(
    event_id: str,
    event: FinancialEvent,
):

    max_retries = 2
    amount_limit = 10000

    reasons = []
    allowed = True

    if event.status == "captured":

        policy_result = {
            "decision": "NO_ACTION",
            "allowed": True,
            "reasons": [
                "Payment is already captured; no action required"
            ],
            "execution_permitted": False,
        }

        record = get_or_create_record(event_id)

        record["policy"] = policy_result

        record["execution"] = {
            "status": "not_required",
            "executed": False,
            "reason": "Payment already captured",
        }

        return {
            "status": "policy_checked",
            "event_id": event_id,
            **policy_result,
        }

    if event.previous_attempts >= max_retries:

        allowed = False

        reasons.append(
            "Maximum retry limit reached"
        )

    if event.amount > amount_limit:

        allowed = False

        reasons.append(
            "Transaction amount exceeds allowed limit"
        )

    if event.status != "failed":

        allowed = False

        reasons.append(
            "Payment is not in a failed state"
        )

    if allowed:

        reasons.append(
            "All policy checks passed"
        )

    policy_result = {
        "decision": (
            "ALLOWED"
            if allowed
            else "BLOCKED"
        ),
        "allowed": allowed,
        "reasons": reasons,
        "execution_permitted": allowed,
    }

    record = get_or_create_record(event_id)

    record["policy"] = policy_result

    return {
        "status": "policy_checked",
        "event_id": event_id,
        **policy_result,
    }


@app.post("/financial-events/{event_id}/execute")
def execute_action(
    event_id: str,
    event: FinancialEvent,
):

    max_retries = 2
    amount_limit = 10000

    if event.status == "captured":

        execution_result = {
            "status": "not_required",
            "executed": False,
            "reason": "Payment already captured",
        }

        record = get_or_create_record(event_id)

        record["execution"] = execution_result

        return {
            "event_id": event_id,
            **execution_result,
        }

    if event.previous_attempts >= max_retries:

        execution_result = {
            "status": "blocked",
            "executed": False,
            "reason": "Maximum retry limit reached",
        }

        record = get_or_create_record(event_id)

        record["execution"] = execution_result

        return {
            "event_id": event_id,
            **execution_result,
        }

    if event.amount > amount_limit:

        execution_result = {
            "status": "blocked",
            "executed": False,
            "reason": (
                "Transaction amount exceeds "
                "allowed limit"
            ),
        }

        record = get_or_create_record(event_id)

        record["execution"] = execution_result

        return {
            "event_id": event_id,
            **execution_result,
        }

    if event.status != "failed":

        execution_result = {
            "status": "blocked",
            "executed": False,
            "reason": "Payment is not in a failed state",
        }

        record = get_or_create_record(event_id)

        record["execution"] = execution_result

        return {
            "event_id": event_id,
            **execution_result,
        }

    action_id = f"act_{uuid.uuid4().hex[:8]}"

    execution_result = {
        "action_id": action_id,
        "action": "request_authentication",
        "status": "executed",
        "executed": True,
        "environment": "development",
    }

    record = get_or_create_record(event_id)

    record["execution"] = execution_result

    return {
        "event_id": event_id,
        **execution_result,
    }


@app.post("/financial-events/{event_id}/verify")
def verify_outcome(
    event_id: str,
    event: FinancialEvent,
):

    actual_status = event.status

    expected_status = "success"

    verified = actual_status == expected_status

    verification_result = {
        "status": (
            "verified"
            if verified
            else "not_verified"
        ),
        "expected": expected_status,
        "actual": actual_status,
        "verified": verified,
    }

    record = get_or_create_record(event_id)

    record["verification"] = verification_result

    return {
        "event_id": event_id,
        **verification_result,
    }


@app.get("/razorpay/payments/{payment_id}")
def get_razorpay_payment(payment_id: str):

    try:

        payment = razorpay_client.payment.fetch(
            payment_id
        )

        return {
            "status": "success",
            "source": "razorpay_test_mode",
            "payment": payment,
        }

    except Exception as exc:

        return {
            "status": "error",
            "source": "razorpay_test_mode",
            "error": str(exc),
        }


@app.post("/razorpay/orders")
def create_razorpay_order(
    amount: int = 500000
):

    try:

        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{uuid.uuid4().hex[:8]}",
        })

        return {
            "status": "success",
            "source": "razorpay_test_mode",
            "order": order,
        }

    except Exception as exc:

        return {
            "status": "error",
            "source": "razorpay_test_mode",
            "error": str(exc),
        }


@app.post(
    "/financial-events/{event_id}/verify-razorpay/{payment_id}"
)
def verify_razorpay_outcome(
    event_id: str,
    payment_id: str,
):

    try:

        payment = razorpay_client.payment.fetch(
            payment_id
        )

        actual_status = payment.get("status")

        expected_status = "captured"

        verified = actual_status == expected_status

        verification_result = {
            "status": (
                "verified"
                if verified
                else "not_verified"
            ),
            "source": "razorpay_test_mode",
            "payment_id": payment_id,
            "expected": expected_status,
            "actual": actual_status,
            "captured": payment.get("captured"),
            "verified": verified,
        }

        record = get_or_create_record(event_id)

        record["verification"] = verification_result

        return {
            "event_id": event_id,
            **verification_result,
        }

    except Exception as exc:

        return {
            "status": "error",
            "source": "razorpay_test_mode",
            "payment_id": payment_id,
            "error": str(exc),
        }


@app.post(
    "/financial-events/from-razorpay/{payment_id}"
)
def create_event_from_razorpay(
    payment_id: str
):

    try:

        payment = razorpay_client.payment.fetch(
            payment_id
        )

        event_id = f"evt_{uuid.uuid4().hex[:8]}"

        event = {
            "payment_id": payment.get("id"),
            "amount": payment.get("amount", 0) / 100,
            "currency": payment.get("currency"),
            "status": payment.get("status"),
            "method": payment.get("method"),
            "captured": payment.get("captured"),
            "order_id": payment.get("order_id"),
            "failure_reason": payment.get("error_reason"),
        }

        record = get_or_create_record(event_id)

        record["event"] = event

        return {
            "status": "received",
            "source": "razorpay_test_mode",
            "event_id": event_id,
            "event": event,
        }

    except Exception as exc:

        return {
            "status": "error",
            "source": "razorpay_test_mode",
            "error": str(exc),
        }


@app.post(
    "/financial-events/from-razorpay/{payment_id}/process"
)
def process_razorpay_payment(
    payment_id: str
):

    try:

        payment = razorpay_client.payment.fetch(
            payment_id
        )

        event_id = f"evt_{uuid.uuid4().hex[:8]}"

        amount_rupees = (
            payment.get("amount", 0) / 100
        )

        event = {
            "payment_id": payment.get("id"),
            "amount": amount_rupees,
            "currency": payment.get("currency"),
            "status": payment.get("status"),
            "method": payment.get("method"),
            "captured": payment.get("captured"),
            "order_id": payment.get("order_id"),
            "failure_reason": payment.get("error_reason"),
        }

        record = get_or_create_record(event_id)

        record["event"] = event

        evidence = {
            "event_id": event_id,
            "source": "razorpay_test_mode",

            "payment": {
                "payment_id": payment.get("id"),
                "order_id": payment.get("order_id"),
                "amount": amount_rupees,
                "currency": payment.get("currency"),
                "status": payment.get("status"),
                "method": payment.get("method"),
                "captured": payment.get("captured"),
                "international": payment.get("international"),
                "error_code": payment.get("error_code"),
                "error_description": payment.get(
                    "error_description"
                ),
                "error_reason": payment.get(
                    "error_reason"
                ),
            },

            "policy_context": {
                "maximum_retries": 2,
                "amount_limit": 10000,
            },
        }

        record["evidence"] = evidence

        if payment.get("status") == "captured":

            decision = {
                "root_cause": "payment_already_captured",
                "recommended_action": "no_action",
                "reason": (
                    "The Razorpay payment is already captured. "
                    "No recovery action is required."
                ),
                "source": "development_ai_stub",
            }

        elif payment.get(
            "error_reason"
        ) == "authentication_required":

            decision = {
                "root_cause": "authentication_required",
                "recommended_action": "request_authentication",
                "reason": (
                    "The payment requires additional "
                    "authentication."
                ),
                "source": "development_ai_stub",
            }

        else:

            decision = {
                "root_cause": "unknown",
                "recommended_action": "escalate",
                "reason": (
                    "Insufficient evidence to determine "
                    "the root cause."
                ),
                "source": "development_ai_stub",
            }

        record["decision"] = decision

        if payment.get("status") == "captured":

            policy = {
                "decision": "NO_ACTION",
                "allowed": True,
                "reasons": [
                    "Payment is already captured; "
                    "no action required"
                ],
                "execution_permitted": False,
            }

            execution = {
                "status": "not_required",
                "executed": False,
                "reason": "Payment already captured",
            }

        else:

            allowed = True
            reasons = []

            if amount_rupees > 10000:

                allowed = False

                reasons.append(
                    "Transaction amount exceeds "
                    "allowed limit"
                )

            if payment.get("status") != "failed":

                allowed = False

                reasons.append(
                    "Payment is not in a failed state"
                )

            if allowed:

                reasons.append(
                    "All policy checks passed"
                )

            policy = {
                "decision": (
                    "ALLOWED"
                    if allowed
                    else "BLOCKED"
                ),
                "allowed": allowed,
                "reasons": reasons,
                "execution_permitted": allowed,
            }

            execution = {
                "status": "not_executed",
                "executed": False,
                "reason": (
                    "Execution requires an explicit "
                    "controlled action"
                ),
            }

        record["policy"] = policy

        record["execution"] = execution

        verified_payment = razorpay_client.payment.fetch(
            payment_id
        )

        actual_status = verified_payment.get(
            "status"
        )

        verified = actual_status == "captured"

        verification = {
            "status": (
                "verified"
                if verified
                else "not_verified"
            ),
            "source": "razorpay_test_mode",
            "payment_id": payment_id,
            "expected": "captured",
            "actual": actual_status,
            "captured": verified_payment.get(
                "captured"
            ),
            "verified": verified,
        }

        record["verification"] = verification

        return {
            "status": "processed",
            "source": "razorpay_test_mode",
            "event_id": event_id,
            "record": record,
        }

    except Exception as exc:

        return {
            "status": "error",
            "source": "razorpay_test_mode",
            "error": str(exc),
        }

@app.post("/financial-events/demo-failure/process")
def process_demo_failure():

    event_id = f"evt_{uuid.uuid4().hex[:8]}"

    event = {
        "payment_id": "pay_demo_failed_001",
        "amount": 5000.0,
        "currency": "INR",
        "status": "failed",
        "method": "card",
        "captured": False,
        "order_id": "order_demo_failed_001",
        "failure_reason": "authentication_required",
        "previous_attempts": 0,
    }

    record = get_or_create_record(event_id)

    record["event"] = event

    record["evidence"] = {
        "event_id": event_id,
        "source": "development_demo",
        "payment": event,
        "policy_context": {
            "maximum_retries": 2,
            "current_attempts": 0,
            "amount_limit": 10000,
            "amount_within_limit": True,
        },
    }

    record["decision"] = {
        "root_cause": "authentication_required",
        "recommended_action": "request_authentication",
        "reason": (
            "The payment requires additional authentication "
            "and no previous attempt has been made."
        ),
        "source": "development_ai_stub",
    }

    record["policy"] = {
        "decision": "ALLOWED",
        "allowed": True,
        "reasons": [
            "All policy checks passed"
        ],
        "execution_permitted": True,
    }

    action_id = f"act_{uuid.uuid4().hex[:8]}"

    record["execution"] = {
        "action_id": action_id,
        "action": "request_authentication",
        "status": "executed",
        "executed": True,
        "environment": "development",
    }

    record["verification"] = {
        "status": "not_verified",
        "source": "development_demo",
        "expected": "success",
        "actual": "failed",
        "verified": False,
    }

    return {
        "status": "processed",
        "source": "development_demo",
        "event_id": event_id,
        "record": record,
    }
@app.get("/audit/{event_id}")
def get_audit(event_id: str):

    record = decision_records.get(event_id)

    if not record:

        return {
            "event_id": event_id,
            "found": False,
        }

    return {
        "event_id": event_id,
        "found": True,
        "record": record,
    }