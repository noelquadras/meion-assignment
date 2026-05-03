import time
import logging
from datetime import datetime, timedelta
from state_machine import State
from payers.mediassist import MediAssistPayer
from payers.starhealth import StarHealthPayer
from payers.paramount import ParamountPayer
from payers.cghs import CGHSPayer
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
            "paramount": ParamountPayer(),
            "cghs": CGHSPayer()
        }

    def _analyze_query(self, query_text):
        """
        Uses a local LLM (via Ollama) to analyze the intent of a TPA query.
        Classifies into AUTO_RESOLVE (document requests) or ESCALATE (clinical questions).
        If AUTO_RESOLVE, also attempts to extract the requested document.
        """
        logger.info(f"🧠 [AI Reasoning] Analyzing TPA query with LLM: '{query_text}'")
        
        prompt = f"""Classify this TPA message. If they are asking for missing documents (like ID proof, insurance card, diagnosis report), respond in this exact format: AUTO_RESOLVE:<document_name>. If it is a complex clinical question, respond with ESCALATE. Message: {query_text}. Answer:"""

        try:
            response = ollama.generate(model="gpt-oss:120b-cloud", prompt=prompt)
            decision = response['response'].strip()
            
            if "AUTO_RESOLVE" in decision.upper():
                parts = decision.split(":", 1)
                doc_name = parts[1].strip() if len(parts) > 1 else "unknown_document"
                
                # Map common names to our internal IDs
                doc_id = "unknown"
                doc_lower = doc_name.lower()
                if "id" in doc_lower: doc_id = "id_proof"
                elif "insurance" in doc_lower or "policy" in doc_lower: doc_id = "insurance_card"
                elif "diagnosis" in doc_lower or "discharge" in doc_lower: doc_id = "diagnosis"
                else: doc_id = doc_name.replace(" ", "_").lower()
                
                logger.info(f"🎯 [AI Decision] Intent: DOCUMENT_REQUEST. Action: AUTO_RESOLVE, Target Doc: {doc_id}")
                return "AUTO_RESOLVE", doc_id
            else:
                logger.warning(f"🎯 [AI Decision] Intent: CLINICAL/COMPLEX. Action: ESCALATE (AI said: {decision})")
                return "ESCALATE", None
        except Exception as e:
            logger.error(f"❌ AI Reasoning Failed: {e}. Falling back to safe escalation.")
            return "ESCALATE", None

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
                    logger.warning(f"⚠️ [Doc Check] FLAGGED missing documents: {missing}. Submitting anyway to demonstrate TPA Query-Back flow.")
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

                raw_response = payer_interface.get_response(case)
                logger.info(f"📥 [TPA Feedback] Received: {raw_response}")

                # Handle both string and dictionary responses for backward compatibility
                if isinstance(raw_response, dict):
                    status = raw_response.get("status")
                    # Map QUERY_BACK to QUERY for the agent's internal state
                    if status == "QUERY_BACK":
                        status = "QUERY"
                else:
                    status = raw_response

                if status == "APPROVED":
                    case.state = State.APPROVED
                elif status == "REJECTED":
                    case.state = State.QUERY_REJECT
                elif status == "QUERY":
                    # Use the reason from the dict if available
                    if isinstance(raw_response, dict):
                        case.query_text = raw_response.get("reason", "Missing diagnosis document")
                    else:
                        case.query_text = "Missing diagnosis document"
                    case.state = State.QUERY
                else:
                    # If TPA hasn't responded yet, wait in this state
                    logger.info("  ... still waiting for TPA response")

            elif case.state == State.QUERY:
                decision, missing_doc = self._analyze_query(case.query_text)
                if decision == "AUTO_RESOLVE":
                    if missing_doc and missing_doc not in case.docs:
                        logger.info(f"📤 [Action] Retrieving missing document '{missing_doc}' from HMS...")
                        # Create a new list to ensure SQLAlchemy detects the change
                        updated_docs = list(case.docs)
                        updated_docs.append(missing_doc)
                        case.docs = updated_docs
                        logger.info(f"✅ [Action] Added '{missing_doc}' to case documents.")
                    case.state = State.RESUBMITTED
                else:
                    logger.warning("🚨 [Escalation] Complex query requires human intervention.")
                    case.state = State.ESCALATED

            elif case.state == State.QUERY_REJECT:
                logger.warning("🚨 [Rejection] TPA rejected the case. Escalating for manual appeal.")
                case.state = State.ESCALATED

            elif case.state == State.RESUBMITTED:
                logger.info("🔄 [Action] Resubmitting corrected documents to TPA.")
                payer_interface.submit(case)
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