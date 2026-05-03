import { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Plus, Activity, FileText, CheckCircle, AlertTriangle, RefreshCw, FileCheck, Server, AlertCircle } from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [patientId, setPatientId] = useState('P-12345');
  const [payer, setPayer] = useState('Medi Assist');
  const [selectedDocs, setSelectedDocs] = useState(['id_proof', 'insurance_card']);
  const [caseId, setCaseId] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ALL_DOCS = [
    { id: 'id_proof', label: 'ID Proof' },
    { id: 'insurance_card', label: 'Insurance Card' },
    { id: 'diagnosis', label: 'Diagnosis Report' }
  ];

  const handleDocToggle = (docId) => {
    setSelectedDocs(prev => 
      prev.includes(docId) ? prev.filter(d => d !== docId) : [...prev, docId]
    );
  };

  useEffect(() => {
    let intervalId;

    const terminalStates = ['APPROVED', 'REJECTED', 'TIMED_OUT', 'ESCALATED'];
    const isTerminal = caseData && terminalStates.includes(caseData.state);
    const isInitial = caseData?.state === 'ADMISSION';

    if (caseId && !isTerminal && !isInitial) {
      intervalId = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/case/${caseId}`);
          setCaseData(response.data);
        } catch (err) {
          console.error("Error polling case:", err);
        }
      }, 1500); // poll every 1.5 seconds
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [caseId, caseData?.state]);

  const handleProcessCase = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 1. Create the case
      const createResponse = await axios.post(`${API_BASE_URL}/create-case/`, {
        patient_id: patientId,
        payer: payer,
        docs: selectedDocs
      });
      const newCaseId = createResponse.data.case_id;
      setCaseId(newCaseId);
      
      // 2. Start the agent immediately
      await axios.post(`${API_BASE_URL}/start-case/${newCaseId}`);
      
      // 3. Fetch current state to trigger polling/UI
      const response = await axios.get(`${API_BASE_URL}/case/${newCaseId}`);
      setCaseData(response.data);
      
      setLoading(false);
    } catch (err) {
      setError(err.message || 'Failed to process case');
      setLoading(false);
    }
  };

  const getStateInfo = (state) => {
    const states = {
      ADMISSION: { label: 'Admission', icon: <Plus size={16} />, type: 'completed' },
      DOC_CHECK: { label: 'Document Check', icon: <FileCheck size={16} />, type: 'active' },
      WAITING_DOCS: { label: 'Waiting for Docs', icon: <FileText size={16} />, type: 'warning' },
      READY: { label: 'Ready for Submission', icon: <CheckCircle size={16} />, type: 'completed' },
      SUBMITTED: { label: 'Submitted to TPA', icon: <Server size={16} />, type: 'active' },
      WAITING_RESPONSE: { label: 'Waiting TPA Response', icon: <RefreshCw size={16} className="animate-spin" />, type: 'active' },
      QUERY: { label: 'TPA Query Received', icon: <AlertCircle size={16} />, type: 'warning' },
      RESUBMITTED: { label: 'Autonomous Resubmission', icon: <RefreshCw size={16} className="animate-spin" />, type: 'active' },
      APPROVED: { label: 'Pre-Auth Approved', icon: <CheckCircle size={16} />, type: 'completed' },
      REJECTED: { label: 'Pre-Auth Rejected', icon: <AlertTriangle size={16} />, type: 'error' },
      TIMED_OUT: { label: 'SLA Timed Out', icon: <AlertTriangle size={16} />, type: 'error' },
      ESCALATED: { label: 'Escalated to Human', icon: <AlertCircle size={16} />, type: 'warning' }
    };
    return states[state] || { label: state, icon: <Activity size={16} />, type: 'active' };
  };

  // Timeline steps to show
  const timelineSteps = ['ADMISSION', 'DOC_CHECK', 'WAITING_RESPONSE', 'QUERY', 'RESUBMITTED', 'APPROVED'];

  // Map all possible states to a rank for logical ordering
  const stateRanks = {
    ADMISSION: 0,
    DOC_CHECK: 1,
    WAITING_DOCS: 1,
    READY: 1.5,
    SUBMITTED: 2,
    WAITING_RESPONSE: 2,
    QUERY: 3,
    RESUBMITTED: 3.5,
    APPROVED: 4,
    REJECTED: 4,
    QUERY_REJECT: 4,
    ESCALATED: 4,
    TIMED_OUT: 4
  };

  const getTimelineItemClass = (step) => {
    if (!caseData) return '';
    
    const currentState = caseData.state;
    
    // Exact match for the active step
    if (currentState === step) {
      if (step === 'APPROVED') return 'completed';
      if (step === 'QUERY') return 'warning';
      return 'active';
    }
    
    const currentRank = stateRanks[currentState] ?? -1;
    const stepRank = stateRanks[step] ?? -1;
    
    // If current state is further along than this step, it's completed
    if (currentRank > stepRank && currentRank !== -1) return 'completed';
    
    // Special handling for QUERY state in timeline if we are at a later state
    if (step === 'QUERY' && currentRank > stateRanks.QUERY) return 'completed';

    // If APPROVED, everything is completed
    if (currentState === 'APPROVED') return 'completed';
    
    return '';
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Meion AI Pre-Auth</h1>
        <p>Intelligent Healthcare Insurance Processing Prototype</p>
      </header>

      <main className="main-content">
        {/* Left Panel: Controls */}
        <section className="panel glass-panel">
          <h2 className="panel-title">
            <Activity className="icon" />
            New Case
          </h2>
          
          <div className="form-group">
            <label>Patient ID</label>
            <input 
              type="text" 
              className="input-field" 
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              disabled={caseId !== null}
            />
          </div>
          
          <div className="form-group">
            <label>TPA / Payer</label>
            <select 
              className="input-field"
              value={payer}
              onChange={(e) => setPayer(e.target.value)}
              disabled={caseId !== null}
            >
              <option value="Medi Assist">Medi Assist</option>
              <option value="Star Health">Star Health</option>
              <option value="Paramount">Paramount</option>
            </select>
          </div>

          <div className="form-group">
            <label>Available Documents</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
              {ALL_DOCS.map(doc => (
                <label key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', opacity: caseId !== null ? 0.6 : 1 }}>
                  <input 
                    type="checkbox" 
                    checked={selectedDocs.includes(doc.id)}
                    onChange={() => handleDocToggle(doc.id)}
                    disabled={caseId !== null}
                    style={{ width: '16px', height: '16px' }}
                  />
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-main)' }}>{doc.label}</span>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <div className="query-alert" style={{ marginTop: '0' }}>
              <div className="query-alert-title"><AlertTriangle size={18}/> Error</div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-main)' }}>{error}</div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
            <button 
              className="btn" 
              onClick={handleProcessCase}
              disabled={loading || caseId !== null}
              style={{ flex: 1 }}
            >
              <Play size={18} />
              Run AI Agent
            </button>
          </div>

          {caseId && (
            <button 
              className="btn btn-secondary" 
              onClick={() => { setCaseId(null); setCaseData(null); }}
              style={{ marginTop: '0.5rem' }}
            >
              Reset / New Case
            </button>
          )}
        </section>

        {/* Right Panel: Tracker */}
        <section className="panel glass-panel" style={{ animationDelay: '0.2s' }}>
          <h2 className="panel-title">
            <Server className="icon" />
            Agent Status Tracker
          </h2>

          {!caseData ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', color: 'var(--text-muted)' }}>
              <Activity size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
              <p>Create a case to start tracking</p>
            </div>
          ) : (
            <div className="status-container">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="case-id-badge">
                  <FileText size={16} />
                  Case #{caseData.id}
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  Payer: <strong style={{ color: 'var(--text-main)' }}>{caseData.payer}</strong>
                </div>
              </div>

              <div className="status-grid">
                <div className="status-card">
                  <span className="status-card-label">Current State</span>
                  <span className={`status-card-value ${caseData.state !== 'APPROVED' && caseData.state !== 'REJECTED' ? 'status-value-animated' : ''}`} style={{ color: caseData.state === 'APPROVED' ? 'var(--success)' : (caseData.state === 'QUERY' ? 'var(--warning)' : '') }}>
                    {getStateInfo(caseData.state).label}
                  </span>
                </div>
                
                <div className="status-card">
                  <span className="status-card-label">Documents</span>
                  <div className="docs-list">
                    {caseData.docs && caseData.docs.map((doc, idx) => (
                      <span key={idx} className="doc-tag">
                        <CheckCircle size={12} color="var(--success)" />
                        {doc.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {caseData.query && (
                <div className="query-alert">
                  <div className="query-alert-title">
                    <Activity size={18} />
                    AI Agent Extracting & Resolving Query
                  </div>
                  <div style={{ fontSize: '0.95rem', lineHeight: '1.5' }}>
                    "{caseData.query}"
                  </div>
                </div>
              )}

              {/* Timeline Visualization */}
              <div className="timeline">
                {timelineSteps.map((step, idx) => {
                  const stateInfo = getStateInfo(step);
                  const statusClass = getTimelineItemClass(step);
                  
                  return (
                    <div key={step} className={`timeline-item ${statusClass}`}>
                      <div className="timeline-dot"></div>
                      <div className="timeline-content">
                        <div className="timeline-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {stateInfo.icon} {stateInfo.label}
                        </div>
                        {statusClass === 'active' && (
                          <div className="timeline-desc">Agent is currently processing this step...</div>
                        )}
                        {statusClass === 'completed' && (
                          <div className="timeline-desc" style={{ color: 'var(--success)' }}>Completed</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
