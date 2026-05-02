import { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Plus, Activity, FileText, CheckCircle, AlertTriangle, RefreshCw, FileCheck, Server, AlertCircle } from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [patientId, setPatientId] = useState('P-12345');
  const [payer, setPayer] = useState('Medi Assist');
  const [caseId, setCaseId] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let intervalId;

    if (caseId && caseData?.state !== 'APPROVED' && caseData?.state !== 'REJECTED' && caseData?.state !== 'TIMED_OUT') {
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

  const handleCreateCase = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.post(`${API_BASE_URL}/create-case/?patient_id=${patientId}&payer=${payer}`);
      setCaseId(response.data.case_id);
      
      // Fetch initial state
      const initialCase = await axios.get(`${API_BASE_URL}/case/${response.data.case_id}`);
      setCaseData(initialCase.data);
      setLoading(false);
    } catch (err) {
      setError(err.message || 'Failed to create case');
      setLoading(false);
    }
  };

  const handleStartCase = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE_URL}/start-case/${caseId}`);
      setLoading(false);
    } catch (err) {
      setError(err.message || 'Failed to start case');
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
      RESUBMITTED: { label: 'Resubmitted Docs', icon: <RefreshCw size={16} />, type: 'active' },
      APPROVED: { label: 'Pre-Auth Approved', icon: <CheckCircle size={16} />, type: 'completed' },
      REJECTED: { label: 'Pre-Auth Rejected', icon: <AlertTriangle size={16} />, type: 'error' },
      TIMED_OUT: { label: 'SLA Timed Out', icon: <AlertTriangle size={16} />, type: 'error' }
    };
    return states[state] || { label: state, icon: <Activity size={16} />, type: 'active' };
  };

  // Timeline steps to show
  const timelineSteps = ['ADMISSION', 'DOC_CHECK', 'WAITING_RESPONSE', 'QUERY', 'APPROVED'];

  const getTimelineItemClass = (step) => {
    if (!caseData) return '';
    
    // Simplistic timeline logic for demo
    if (caseData.state === step) {
      if (step === 'APPROVED') return 'completed';
      if (step === 'QUERY') return 'warning';
      return 'active';
    }
    
    const currentIndex = timelineSteps.indexOf(caseData.state);
    const stepIndex = timelineSteps.indexOf(step);
    
    // If current state is further along, this step is completed
    if (currentIndex > stepIndex && currentIndex !== -1) return 'completed';
    
    // If APPROVED, everything before is completed
    if (caseData.state === 'APPROVED' && stepIndex !== -1) return 'completed';
    
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

          {error && (
            <div className="query-alert" style={{ marginTop: '0' }}>
              <div className="query-alert-title"><AlertTriangle size={18}/> Error</div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-main)' }}>{error}</div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
            <button 
              className="btn" 
              onClick={handleCreateCase}
              disabled={loading || caseId !== null}
              style={{ flex: 1 }}
            >
              <Plus size={18} />
              Create Case
            </button>
            
            <button 
              className="btn btn-secondary" 
              onClick={handleStartCase}
              disabled={loading || caseId === null || caseData?.state !== 'ADMISSION'}
              style={{ flex: 1, borderColor: caseId !== null && caseData?.state === 'ADMISSION' ? 'var(--primary)' : 'var(--border-color)', color: caseId !== null && caseData?.state === 'ADMISSION' ? 'var(--primary)' : 'var(--text-main)' }}
            >
              <Play size={18} />
              Start AI Agent
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
                    <AlertCircle size={18} />
                    TPA Query Addressed by Agent
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
