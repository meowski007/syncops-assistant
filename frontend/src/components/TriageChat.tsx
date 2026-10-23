import React, { useState } from 'react';
import { api, RagTriageResponse, Incident } from '../api';
import { Send, Bot, BookOpen, AlertOctagon, CheckCircle, ShieldCheck } from 'lucide-react';

interface Props {
  selectedIncident: Incident | null;
}

export const TriageChat: React.FC<Props> = ({ selectedIncident }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RagTriageResponse | null>(null);

  const handleTriage = async (customQuery?: string) => {
    const q = customQuery !== undefined ? customQuery : query;
    setLoading(true);
    try {
      const res = await api.postRagTriage(selectedIncident?.id, q || undefined);
      setResponse(res);
    } catch (err: any) {
      alert(`Triage request failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
        <Bot size={20} color="#38bdf8" />
        <h3 style={{ margin: 0, fontSize: '16px', color: '#f8fafc' }}>
          Autonomous SRE Triage Assistant (Grounded RAG)
        </h3>
      </div>

      {selectedIncident && (
        <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px', marginBottom: '14px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>Active Incident Context:</div>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>
            [{selectedIncident.severity}] {selectedIncident.id}: {selectedIncident.title}
          </div>
          <button
            onClick={() => handleTriage()}
            disabled={loading}
            style={{
              marginTop: '8px',
              backgroundColor: '#0284c7',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Analyzing Telemetry & Runbooks...' : 'Run Automated Grounded Triage'}
          </button>
        </div>
      )}

      {/* Query Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) handleTriage();
        }}
        style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}
      >
        <input
          type="text"
          placeholder="Ask an operational question (e.g. 'How to mitigate payload timeouts on iOS?')"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            flex: 1,
            backgroundColor: '#0f172a',
            border: '1px solid #475569',
            borderRadius: '6px',
            padding: '10px 14px',
            color: '#f8fafc',
            fontSize: '13px',
          }}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          style={{
            backgroundColor: '#0284c7',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            padding: '0 16px',
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Send size={16} />
        </button>
      </form>

      {/* RAG Response View */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
          Querying SQLite telemetry and scanning vector index across 13 operational runbooks...
        </div>
      ) : response ? (
        <div style={{ backgroundColor: '#0f172a', borderRadius: '8px', padding: '16px', border: '1px solid #334155' }}>
          {response.refusal ? (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', color: '#fbbf24' }}>
              <AlertOctagon size={20} />
              <div>
                <strong style={{ fontSize: '14px' }}>Guardrail Refusal: Insufficient Runbook Evidence</strong>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#cbd5e1' }}>{response.refusal_reason}</p>
              </div>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#38bdf8' }}>{response.summary}</span>
                <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 600 }}>Confidence: {Math.round(response.confidence * 100)}%</span>
              </div>

              {/* Empirical Facts */}
              {response.empirical_facts.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Verified Telemetry Facts (Database)
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#cbd5e1' }}>
                    {response.empirical_facts.map((fact, idx) => (
                      <li key={idx} style={{ marginBottom: '2px' }}>{fact}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommended Mitigations */}
              {response.recommended_mitigations.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Recommended Operational Actions (Runbook Grounded)
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#f8fafc' }}>
                    {response.recommended_mitigations.map((act, idx) => (
                      <li key={idx} style={{ marginBottom: '4px' }}>{act}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Citations Panel */}
              {response.citations.length > 0 && (
                <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <BookOpen size={12} />
                    Verified Source Citations
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {response.citations.map((c, idx) => (
                      <div key={idx} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', padding: '4px 8px', fontSize: '11px', color: '#94a3b8' }}>
                        📖 <code style={{ color: '#38bdf8' }}>{c.source_file}</code> — {c.section_heading} ({Math.round(c.relevance_score * 100)}% match)
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '12px', fontStyle: 'italic' }}>
                ⚠️ Advisory AI output. Human SRE authorization is required before production mutations.
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '13px' }}>
          Select an incident from the table above or ask a diagnostic question to begin automated RAG triage.
        </div>
      )}
    </div>
  );
};
