# AI Insurance Agent: Cashless Pre-Authorization Prototype

An automated AI-driven workflow designed to handle insurance pre-authorizations for an 80-bed hospital. This prototype demonstrates a state-machine based approach to reducing manual billing workload and meeting IRDAI's 1-hour response mandate.

## 🚀 Overview
The billing team currently handles 30 admissions/day manually across various portals and email. This leads to:
- **Solution:** The AI Agent acts as a "Unified Submission Layer" that:
1. **Orchestrates** the workflow from admission to discharge via a state machine.
2. **Automates** document completeness checks before submission.
3. **Interfaces** with various TPA endpoints (API or Mocked Portal/Email).
4. **Reasons** about TPA queries to auto-resolve routine issues (e.g., missing ID proof) or escalate complex clinical queries to the billing team.

## 2. Agent Design & Reasoning
The agent is implemented as a dedicated class (`InsuranceAgent`) that separates **perception** (receiving TPA feedback) from **reasoning** (analyzing intent).

- **Intent Extraction:** The agent uses a simulated reasoning step (`_analyze_query`) to extract the intent from free-text TPA queries. In a production environment, this would be powered by an LLM (e.g., GPT-4 or Gemini).
- **Autonomous Recovery:** If the intent is identified as a `DOCUMENT_REQUEST`, the agent triggers a retrieval action and resubmits without human intervention.
- **Backend:** FastAPI (Python)
- **Database:** SQLite with SQLAlchemy ORM
- **Logic:** `InsuranceAgent` class with simulated AI intent extraction and state-machine transitions.
- **Logging:** Full audit trail with "Reasoning" and "Decision" logs for transparency.
- **Demo:** Python script using `requests` to trigger and monitor the workflow.

## 📁 Project Structure
- `main.py`: FastAPI endpoints for case management.
- `agent.py`: The core AI agent logic and state transition loop.
- `state_machine.py`: Definition of case states (Admission, Doc Check, Query, etc.).
- `models.py`: Database schema for insurance cases.
- `payers/`: Payer-specific submission logic (Medi Assist, Star Health, etc.).
- `ARCHITECTURE.md`: Detailed architecture, problem framing, and guardrails.

## 🏃 Getting Started

### 1. Prerequisites
- Python 3.10+
- Installed dependencies:
  ```bash
  pip install fastapi uvicorn sqlalchemy requests
  ```

### 2. Run the Application
Start the FastAPI server in one terminal:
```bash
uvicorn main:app --reload
```

### 3. Run the Demo
In a second terminal, run the automated demo script:
```bash
python run_demo.py
```

## 📊 Expected Output
When you run the demo, the terminal logs will show the agent's real-time "thinking":
- `🤖 [Agent Start]`: Orchestrating the case.
- `🔍 [Doc Check]`: Identifying and auto-fetching missing documents.
- `🧠 [Agent Reasoning]`: Analyzing TPA query intent using simulated AI.
- `🎯 [Agent Decision]`: Making a decision (Auto-resolve vs. Escalate).
- `🏁 [Agent Finish]`: Final workflow status.

## 🛡️ Guardrails
The agent follows strict guardrails:
- **Autonomous**: Data entry, doc checks, standard portal uploads.
- **Human Required**: Clinical disagreements, manual appeals, and final discharge sign-off.
Check `ARCHITECTURE.md` for the full guardrails table.
