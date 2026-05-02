import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_demo():
    print("Starting AI Insurance Agent Prototype Demo...")
    
    # 1. Trigger Admission
    print("\n[1/3] Triggering admission for Patient P-999...")
    try:
        response = requests.post(f"{BASE_URL}/create-case/", params={"patient_id": "P-999", "payer": "mediassist"})
        case_id = response.json()["case_id"]
        print(f"Case created with ID: {case_id}")
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        print("Make sure the FastAPI server is running (uvicorn main:app --reload)")
        return

    # 2. Start Workflow
    print(f"\n[2/3] Starting pre-auth workflow for Case {case_id}...")
    requests.post(f"{BASE_URL}/start-case/{case_id}")
    
    # 3. Poll for results
    print("\n[3/3] Polling for state transitions (Watch the terminal logs for timestamps)...")
    
    last_state = None
    while True:
        case_data = requests.get(f"{BASE_URL}/case/{case_id}").json()
        current_state = case_data["state"]
        
        if current_state != last_state:
            print(f"Current State: {current_state}")
            last_state = current_state
            
        if current_state in ["APPROVED", "REJECTED", "ESCALATED", "TIMED_OUT"]:
            print(f"\nWorkflow Terminated: {current_state}")
            break
            
        time.sleep(2)

if __name__ == "__main__":
    run_demo()
