import time
import logging
from datetime import datetime, timedelta
from state_machine import State
from payers.mediassist import MediAssistPayer
from payers.starhealth import StarHealthPayer
from payers.paramount import ParamountPayer
import ollama

# Configure logging to output to terminal with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("InsuranceAgent")

REQUIRED_DOCS = ["id_proof", "insurance_card", "diagnosis"]
TIMEOUT_THRESHOLD_SEC = 15 # Simulated 1-hour mandate for the prototype

class InsuranceAgent:
    """
    An AI-driven agent that manages the insurance pre-auth workflow.
    It uses a state-machine to maintain context and a 'reasoning' step
    to handle non-deterministic events like TPA queries.
    """
    def __init__(self):
        self.payer_map = {
            "mediassist": MediAssistPayer(),
            "starhealth": StarHealthPayer(),
            "paramount": ParamountPayer()
        }

    def _analyze_query(self, query_text):
        """
        Uses local Ollama (qwen2.5-coder:1.5b-base) to analyze the intent of a TPA query.
        """
        logger.info(f"🧠 [AI Reasoning] Analyzing with qwen2.5-coder: '{query_text}'")
        
        prompt = f"""
        Instructions: You are a hospital billing agent. Analyze the TPA message and return EXACTLY ONE WORD.
        - If they ask for documents, reports, or ID: return 'AUTO_RESOLVE'
        - If they ask clinical questions or medical details: return 'ESCALATE'

        TPA Message: "{query_text}"
        Decision (one word only):"""

        try:
            response = ollama.generate(model="qwen2.5-coder:1.5b-base", prompt=prompt)
            decision = response['response'].strip().upper()
            
            if "AUTO_RESOLVE" in decision:
                logger.info("🎯 [AI Decision] Intent: DOCUMENT_REQUEST. Action: AUTO_RESOLVE")
                return "AUTO_RESOLVE"
            else:
                logger.warning(f"🎯 [AI Decision] Intent: CLINICAL/COMPLEX. Action: ESCALATE (AI said: {decision})")
                return "ESCALATE"
        except Exception as e:
            logger.error(f"❌ AI Reasoning Failed: {e}. Falling back to safe escalation.")
            return "ESCALATE"

    def process_case(self, db, case):
        logger.info(f"🤖 [Agent Start] Orchestrating Case {case.id} for {case.payer}")
        
        payer_key = case.payer.lower().replace(" ", "")
        payer_interface = self.payer_map.get(payer_key)
        if not payer_interface:
            logger.error(f"Unknown payer: {case.payer}")
            return

        while case.state not in [State.APPROVED, State.REJECTED, State.ESCALATED, State.TIMED_OUT]:
            logger.info(f"⏳ [Current State: {case.state}]")

            if case.state == State.ADMISSION:
                case.state = State.DOC_CHECK

            elif case.state == State.DOC_CHECK:
                missing = [d for d in REQUIRED_DOCS if d not in case.docs]
                if missing:
                    logger.warning(f"⚠️ [Doc Check] FLAGGED missing documents: {missing}")
                    logger.info(f"📤 [Action] Requesting missing docs from HMS...")
                    case.docs.extend(missing)
                    logger.info("✅ [Action] Retrieved missing docs from HMS.")
                    case.state = State.READY
                else:
                    logger.info("✅ [Doc Check] All documents present")
                    case.state = State.READY

            elif case.state == State.READY:
                logger.info(f"📡 [Action] Submitting case data to {case.payer} TPA...")
                payer_interface.submit(case)
                case.submitted_at = datetime.now()
                case.state = State.WAITING_RESPONSE

            elif case.state == State.WAITING_RESPONSE:
                # Compliance Check: Monitor the 1-hour mandate
                if case.submitted_at:
                    elapsed = (datetime.now() - case.submitted_at).total_seconds()
                    if elapsed > TIMEOUT_THRESHOLD_SEC:
                        logger.error(f"⚠️ [SLA BREACH] Case {case.id} has exceeded the 1-hour mandate!")
                        case.state = State.TIMED_OUT
                        db.commit()
                        break

                response = payer_interface.get_response(case)
                logger.info(f"📥 [TPA Feedback] Received: {response}")

                if response == "APPROVED":
                    case.state = State.APPROVED
                elif response == "REJECTED":
                    case.state = State.QUERY_REJECT
                elif response == "QUERY":
                    case.query_text = "Missing diagnosis document"
                    case.state = State.QUERY
                else:
                    # If TPA hasn't responded yet, wait in this state
                    logger.info("  ... still waiting for TPA response")

            elif case.state == State.QUERY:
                decision = self._analyze_query(case.query_text)
                if decision == "AUTO_RESOLVE":
                    case.state = State.RESUBMITTED
                else:
                    logger.warning("🚨 [Escalation] Complex query requires human intervention.")
                    case.state = State.ESCALATED

            elif case.state == State.QUERY_REJECT:
                logger.warning("🚨 [Rejection] TPA rejected the case. Escalating for manual appeal.")
                case.state = State.ESCALATED

            elif case.state == State.RESUBMITTED:
                logger.info("🔄 [Action] Resubmitting corrected documents to TPA.")
                case.submitted_at = datetime.now() # Reset clock on resubmission
                case.state = State.WAITING_RESPONSE

            db.commit()
            db.refresh(case)
            time.sleep(3) # Loop speed
        
        logger.info(f"🏁 [Agent Finish] Workflow terminated with status: {case.state}")

# Global agent instance
agent = InsuranceAgent()

def process_case(db, case):
    """Entry point for the background task"""
    agent.process_case(db, case)