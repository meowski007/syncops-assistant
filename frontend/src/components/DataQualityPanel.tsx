import React, { useState, useEffect } from 'react';
import { api, DataQualitySummary } from '../api';
import { ShieldCheck, ShieldAlert, Database, Lock } from 'lucide-react';

export const DataQualityPanel: React.FC = () => {
  const [data, setData] = useState<DataQualitySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    api
      .getDataQuality()
      .then((res) => {
        if (mounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return null;
  if (!data) return null;

  const isPassed = data.status === 'PASSED';
  const isWarning = data.status === 'WARNING';

  return (
    <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isPassed ? <ShieldCheck size={20} color="#10b981" /> : <ShieldAlert size={20} color="#fbbf24" />}
          <h3 style={{ margin: 0, fontSize: '16px', color: '#f8fafc' }}>
            Data Quality & Governance Audit Status
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ backgroundColor: isPassed ? '#10b98122' : '#f59e0b22', color: isPassed ? '#10b981' : '#fbbf24', padding: '3px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 700 }}>
            {data.status}
          </span>
          <span style={{ backgroundColor: '#38bdf822', color: '#38bdf8', padding: '3px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Lock size={12} />
            HMAC PII MASKING ACTIVE
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '14px' }}>
        <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Total Processed</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>{data.total_records}</div>
        </div>
        <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Accepted (Clean Layer)</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981' }}>{data.accepted_records}</div>
        </div>
        <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Quarantined (Dead-Letter)</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: data.rejected_records > 0 ? '#ef4444' : '#64748b' }}>
            {data.rejected_records}
          </div>
        </div>
        <div style={{ backgroundColor: '#0f172a', padding: '10px', borderRadius: '6px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Warnings Flagged</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: data.warning_count > 0 ? '#fbbf24' : '#64748b' }}>
            {data.warning_count}
          </div>
        </div>
      </div>

      <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
        <span>Last Audit Run: <code>{data.last_run_id || 'Initial'}</code></span>
        <span>Lineage Layer: SQLite Staging ➔ Clean Analytical Store</span>
      </div>
    </div>
  );
};
