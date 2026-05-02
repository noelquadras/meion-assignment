import time
import threading
import logging
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import ollama

# ────────────────────────────────────────────
# MOCK TPA SERVER (runs on port 9000)
# ────────────────────────────────────────────
mock_tpa = FastAPI()

submission_count = 0

class TPAResponse(BaseModel):
    status: str
    message: str | None = None
    auth_code: str | None = None

@mock_tpa.post("/mediassist/submit")
async def mediassist_submit(request: Request):
    global submission_count
    submission_count += 1
    body = await request.json()

    # First submission → QUERY_BACK
    if submission_count == 1:
        return {"status": "QUERY", "message": "Please upload diagnosis report"}

    # Resubmission → APPROVED
    return {"status": "APPROVED", "auth_code": "MA-12345"}

@mock_tpa.get("/health")
async def health():
    return {"status": "ok"}


def start_mock_server():
    config = uvicorn.Config(mock_tpa, host="127.0.0.1", port=9000, log_level="error")
    server = uvicorn.Server(config)
    server.run()


# ────────────────────────────────────────────
# DEMO CONFIGURATION
# ────────────────────────────────────────────
MOCK_TPA_URL = "http://127.0.0.1:9000/mediassist/submit"
REQUIRED_DOCS = ["id_proof", "insurance_card", "diagnosis"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Demo")

# ────────────────────────────────────────────
# HARD CODED ADMISSION DATA
# ────────────────────────────────────────────
admission = {
    "patient_id": "P-999",
    "patient_name": "Rajesh Kumar",
    "age": 45,
    "diagnosis": "Acute appendicitis",
    "estimated_cost": 85000,
    "payer": "Medi Assist",
    "insurance_policy": "MA-POL-774321",
    "admitting_doctor": "Dr. Priya Sharma",
    "ward": "General Ward, Bed 12"
}

# Initial docs from HMS (missing diagnosis)
available_docs = ["id_proof", "insurance_card"]


# ────────────────────────────────────────────
# STATE MACHINE
# ────────────────────────────────────────────
class State:
    ADMISSION = "ADMISSION"
    DOC_CHECK = "DOC_CHECK"
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    WAITING_RESPONSE = "WAITING_RESPONSE"
    QUERY = "QUERY"
    RESUBMITTED = "RESUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    TIMED_OUT = "TIMED_OUT"


state = State.ADMISSION


def transition(new_state):
    global state
    old = state
    state = new_state
    logger.info(f"🔀 STATE: {old} → {new_state}")


# ────────────────────────────────────────────
# AGENT LOGIC
# ────────────────────────────────────────────
def check_documents():
    logger.info("📋 [Doc Check] Verifying document completeness...")
    missing = [d for d in REQUIRED_DOCS if d not in available_docs]

    if missing:
        logger.info(f"⚠️  [Doc Check] FLAGGED missing documents: {missing}")
        logger.info(f"    Required: {REQUIRED_DOCS}")
        logger.info(f"    Available: {available_docs}")
        logger.info("📥 [Action] Requesting missing docs from HMS...")
        time.sleep(1)
        available_docs.extend(missing)
        logger.info(f"✅ [Action] Retrieved: {missing}")
    else:
        logger.info("✅ [Doc Check] All documents present")

    return missing


def submit_to_tpa(case_data):
    logger.info(f"📡 [Submit] POST {MOCK_TPA_URL}")
    logger.info(f"    Payload: patient={case_data['patient_id']}, "
                f"policy={case_data['insurance_policy']}, "
                f"cost=₹{case_data['estimated_cost']:,}")

    response = requests.post(MOCK_TPA_URL, json=case_data, timeout=5)
    return response.json()


def analyze_query(message):
    logger.info(f"🧠 [AI Reasoning] Analyzing TPA query with LLM: '{message}'")
    
    prompt = f"""Classify this TPA message as AUTO_RESOLVE or ESCALATE. AUTO_RESOLVE means they need a document. ESCALATE means clinical question. Message: {message}. Answer with one word only:"""

    try:
        response = ollama.generate(model="gpt-oss:120b-cloud", prompt=prompt)
        decision = response['response'].strip().upper()
        
        if "AUTO_RESOLVE" in decision:
            logger.info("🎯 [AI Decision] Intent: DOCUMENT_REQUEST → Action: AUTO_RESOLVE")
            return "AUTO_RESOLVE"
        else:
            logger.info(f"🎯 [AI Decision] Intent: CLINICAL/COMPLEX → Action: ESCALATE (AI said: {decision})")
            return "ESCALATE"
    except Exception as e:
        logger.error(f"❌ AI Reasoning Failed: {e}. Falling back to ESCALATE.")
        return "ESCALATE"


# ────────────────────────────────────────────
# MAIN DEMO
# ────────────────────────────────────────────
def run_demo():
    global submission_count
    submission_count = 0

    print()
    print("=" * 65)
    print("  MEION -- AI Insurance Pre-Auth Prototype Demo")
    print("  Payer: Medi Assist  |  Workflow: Query-Back -> Approval")
    print("=" * 65)
    print()

    # ── Start mock TPA server ──
    logger.info("[SERVER] Starting mock TPA server on port 9000...")
    tpa_thread = threading.Thread(target=start_mock_server, daemon=True)
    tpa_thread.start()
    time.sleep(2)

    # Verify it's up
    try:
        requests.get("http://127.0.0.1:9000/health", timeout=3)
        logger.info("✅ Mock TPA server is running")
    except Exception as e:
        logger.error(f"❌ Mock TPA server failed to start: {e}")
        return

    print()
    logger.info(f"🏥 [ADMISSION] Patient {admission['patient_id']} — "
                f"{admission['patient_name']}, {admission['age']}y/o")
    logger.info(f"    Diagnosis: {admission['diagnosis']}")
    logger.info(f"    Payer: {admission['payer']}  |  Policy: {admission['insurance_policy']}")
    logger.info(f"    Estimated Cost: ₹{admission['estimated_cost']:,}")
    logger.info(f"    Doctor: {admission['admitting_doctor']}  |  {admission['ward']}")
    transition(State.DOC_CHECK)

    print()
    missing = check_documents()
    transition(State.READY)

    print()
    transition(State.SUBMITTED)
    response = submit_to_tpa(admission)
    logger.info(f"📨 [TPA Response] {response}")
    transition(State.WAITING_RESPONSE)

    print()
    if response["status"] == "APPROVED":
        logger.info(f"✅ [APPROVED] Auth code: {response.get('auth_code')}")
        transition(State.APPROVED)
    elif response["status"] == "QUERY":
        logger.info(f"❓ [QUERY-BACK] TPA says: {response['message']}")
        transition(State.QUERY)

        print()
        decision = analyze_query(response["message"])

        if decision == "AUTO_RESOLVE":
            print()
            logger.info("🔄 [Resubmit] Documents corrected, re-sending to TPA...")
            transition(State.RESUBMITTED)

            response = submit_to_tpa(admission)
            logger.info(f"📨 [TPA Response] {response}")
            transition(State.WAITING_RESPONSE)

            print()
            if response["status"] == "APPROVED":
                logger.info(f"✅ [APPROVED] Auth code: {response.get('auth_code')}")
                logger.info("    Patient cleared for treatment. Discharge process can begin.")
                transition(State.APPROVED)
            else:
                logger.info(f"⚠️  Unexpected response on resubmit: {response}")
                transition(State.ESCALATED)
        else:
            print()
            logger.info("🚨 [ESCALATED] Clinical query — routing to human billing team.")
            transition(State.ESCALATED)
    elif response["status"] == "REJECTED":
        logger.info("❌ [REJECTED] TPA rejected the pre-auth.")
        logger.info("🚨 [ESCALATED] Routing to human for appeal.")
        transition(State.REJECTED)
        transition(State.ESCALATED)

    print()
    print("=" * 65)
    logger.info(f"🏁 [DONE] Workflow ended in state: {state}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    run_demo()
