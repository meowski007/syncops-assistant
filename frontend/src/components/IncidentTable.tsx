import React, { useState } from 'react';
import { Incident } from '../api';
import { AlertTriangle, Filter } from 'lucide-react';

interface Props {
  incidents: Incident[];
  loading: boolean;
  onSelectIncident: (inc: Incident) => void;
  selectedId: string | null;
}

export const IncidentTable: React.FC<Props> = ({ incidents, loading, onSelectIncident, selectedId }) => {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sevFilter, setSevFilter] = useState('ALL');

  const filtered = incidents.filter((inc) => {
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (sevFilter !== 'ALL' && inc.severity !== sevFilter) return false;
    return true;
  });

  const getSeverityBadge = (sev: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      SEV1: { bg: '#ef444422', text: '#ef4444' },
      SEV2: { bg: '#f9731622', text: '#f97316' },
      SEV3: { bg: '#eab30822', text: '#eab308' },
      SEV4: { bg: '#3b82f622', text: '#3b82f6' },
    };
    const c = colors[sev] || { bg: '#64748b22', text: '#94a3b8' };
    return (
      <span style={{ backgroundColor: c.bg, color: c.text, padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700 }}>
        {sev}
      </span>
    );
  };

  const getStatusBadge = (st: string) => {
    const isInvestigating = st === 'INVESTIGATING' || st === 'DETECTED';
    return (
      <span style={{ backgroundColor: isInvestigating ? '#f59e0b22' : '#10b98122', color: isInvestigating ? '#fbbf24' : '#34d399', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>
        {st}
      </span>
    );
  };

  return (
    <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={20} color="#38bdf8" />
          <h3 style={{ margin: 0, fontSize: '16px', color: '#f8fafc' }}>Active SRE Incidents Directory</h3>
        </div>
        
        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#94a3b8' }}>
            <Filter size={14} />
            <span>Severity:</span>
            <select
              value={sevFilter}
              onChange={(e) => setSevFilter(e.target.value)}
              style={{ backgroundColor: '#0f172a', color: '#f8fafc', border: '1px solid #475569', borderRadius: '6px', padding: '4px 8px', fontSize: '12px' }}
            >
              <option value="ALL">All Severities</option>
              <option value="SEV1">SEV1</option>
              <option value="SEV2">SEV2</option>
              <option value="SEV3">SEV3</option>
              <option value="SEV4">SEV4</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#94a3b8' }}>
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ backgroundColor: '#0f172a', color: '#f8fafc', border: '1px solid #475569', borderRadius: '6px', padding: '4px 8px', fontSize: '12px' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="DETECTED">DETECTED</option>
              <option value="MITIGATED">MITIGATED</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>Loading incident telemetry...</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>No incidents matching the selected filters.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                <th style={{ padding: '10px' }}>Incident ID</th>
                <th style={{ padding: '10px' }}>Title</th>
                <th style={{ padding: '10px' }}>Severity</th>
                <th style={{ padding: '10px' }}>Status</th>
                <th style={{ padding: '10px' }}>Cohort</th>
                <th style={{ padding: '10px' }}>Category</th>
                <th style={{ padding: '10px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inc) => (
                <tr
                  key={inc.id}
                  style={{
                    borderBottom: '1px solid #1e293b',
                    backgroundColor: selectedId === inc.id ? '#33415555' : 'transparent',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  <td style={{ padding: '12px 10px', fontWeight: 600, color: '#38bdf8' }}>{inc.id}</td>
                  <td style={{ padding: '12px 10px', color: '#f8fafc', maxWidth: '300px' }}>{inc.title}</td>
                  <td style={{ padding: '12px 10px' }}>{getSeverityBadge(inc.severity)}</td>
                  <td style={{ padding: '12px 10px' }}>{getStatusBadge(inc.status)}</td>
                  <td style={{ padding: '12px 10px', color: '#cbd5e1' }}>{inc.affected_cohort}</td>
                  <td style={{ padding: '12px 10px', color: '#94a3b8' }}>{inc.failure_category}</td>
                  <td style={{ padding: '12px 10px' }}>
                    <button
                      onClick={() => onSelectIncident(inc)}
                      style={{
                        backgroundColor: selectedId === inc.id ? '#0284c7' : '#334155',
                        color: '#f8fafc',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        cursor: 'pointer',
                        fontWeight: 500,
                      }}
                    >
                      {selectedId === inc.id ? 'Active Focus' : 'Triage with RAG'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
