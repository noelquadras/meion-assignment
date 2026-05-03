import time
import logging
import random
from payers.base import BasePayer

logger = logging.getLogger("Payer.MediAssist")

class MediAssistPayer(BasePayer):
    """
    Medi Assist — Portal + Email channel adapter.
    Refactored to provide realistic, input-driven behavior for AI agent testing.
    """

    CHANNEL = "portal_email"
    REQUIRED_DOCS = ["id_proof", "insurance_card", "diagnosis"]

    def __init__(self):
        super().__init__()
        # Tracks submission attempts per case ID to simulate stateful TPA behavior
        self.submission_counts = {}

    def submit(self, case) -> dict:
        """
        Simulates logging into the Medi Assist portal and uploading documents.
        Returns a submission acknowledgement with a reference number.
        """
        case_id = getattr(case, 'id', 'unknown')
        self.submission_counts[case_id] = self.submission_counts.get(case_id, 0) + 1
        
        logger.info(f"🌐 [MediAssist Portal] Navigating to https://provider.mediassist.in/dashboard")
        time.sleep(1.2)  # Simulate network and page load latency
        
        logger.info(f"📝 [MediAssist Portal] Filling pre-auth form for Patient ID: {getattr(case, 'patient_id', 'N/A')}")
        
        # Simulate document upload sequence
        case_docs = getattr(case, 'docs', [])
        logger.info(f"📤 [MediAssist Portal] Uploading {len(case_docs)} document(s) to secure server...")
        for doc in case_docs:
            time.sleep(0.4)  # Simulate upload time per file
            logger.info(f"   -> [UPLOADED] {doc}")
            
        logger.info(f"✅ [MediAssist Portal] Submission successful. Generated Reference: MA-REF-{case_id}")
        
        return {
            "status": "SUBMITTED",
            "reference": f"MA-REF-{case_id}",
            "attempt": self.submission_counts[case_id],
            "timestamp": time.time()
        }

    def get_response(self, case) -> dict:
        """
        Simulates checking the portal or polling the hospital email for a TPA decision.
        Decision logic is driven by the presence of REQUIRED_DOCS and submission history.
        """
        case_id = getattr(case, 'id', 'unknown')
        # Normalize provided documents for comparison
        provided_docs = [str(d).strip().lower() for d in getattr(case, 'docs', [])]
        submission_count = self.submission_counts.get(case_id, 1)

        logger.info(f"📧 [MediAssist Email] Polling hospital inbox for updates on MA-REF-{case_id}...")
        time.sleep(2.0)  # Simulate realistic TPA processing/review delay

        # Identify missing mandatory documents
        missing_docs = [req for req in self.REQUIRED_DOCS if req.lower() not in provided_docs]
        num_missing = len(missing_docs)

        # Realistic TPA Logic:
        # 1. All docs present -> APPROVED
        if num_missing == 0:
            status = "APPROVED"
            reason = "All mandatory documents verified. Medical necessity established."
        
        # 2. 1-2 docs missing -> QUERY_BACK (TPA asks for more info)
        elif 1 <= num_missing <= 2:
            status = "QUERY_BACK"
            reason = f"Missing mandatory documents: {', '.join(missing_docs)}"
            
            # Realism: On first submission, TPAs are more likely to query even for minor issues.
            # On resubmission, if it's still missing, we might reject, but following prompt rules:
            if submission_count > 1:
                logger.info(f"🔍 [MediAssist Internal] Reviewing resubmission attempt #{submission_count}...")
        
        # 3. More than 2 docs missing -> REJECTED (Initial submission was too sparse)
        else:
            status = "REJECTED"
            reason = f"Incomplete submission. Multiple mandatory documents missing: {', '.join(missing_docs)}"

        # Add slight variability: 10% chance of a random clinical query even if docs are present
        if status == "APPROVED" and random.random() < 0.10:
            status = "QUERY_BACK"
            reason = "Additional clarification required: Please provide detailed clinical indication for admission."

        response = {
            "status": status,
            "reason": reason,
            "case_id": case_id,
            "processed_at": time.time(),
            "channel": self.CHANNEL
        }

        logger.info(f"📨 [MediAssist] Received Response: {status} | Reason: {reason}")
        return response
