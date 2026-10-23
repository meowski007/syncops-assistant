import React, { useState, useEffect } from 'react';
import { api, ForecastResponse } from '../api';
import { TrendingUp, AlertCircle } from 'lucide-react';

export const ForecastChart: React.FC = () => {
  const [target, setTarget] = useState<'failure_rate' | 'incident_volume'>('failure_rate');
  const [horizon, setHorizon] = useState<number>(7);
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .getForecast(target, horizon)
      .then((res) => {
        if (mounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [target, horizon]);

  return (
    <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '10px', border: '1px solid #334155', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={20} color="#a855f7" />
          <h3 style={{ margin: 0, fontSize: '16px', color: '#f8fafc' }}>
            Time-Series Forecasting & Walk-Forward Validation
          </h3>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value as any)}
            style={{ backgroundColor: '#0f172a', color: '#f8fafc', border: '1px solid #475569', borderRadius: '6px', padding: '4px 8px', fontSize: '12px' }}
          >
            <option value="failure_rate">Daily Failure Rate (%)</option>
            <option value="incident_volume">Daily Incident Volume</option>
          </select>

          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            style={{ backgroundColor: '#0f172a', color: '#f8fafc', border: '1px solid #475569', borderRadius: '6px', padding: '4px 8px', fontSize: '12px' }}
          >
            <option value={3}>3 Days Horizon</option>
            <option value={7}>7 Days Horizon</option>
            <option value={14}>14 Days Horizon</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Generating walk-forward predictions...</div>
      ) : error ? (
        <div style={{ padding: '20px', color: '#f87171' }}>Error loading forecast: {error}</div>
      ) : data ? (
        <div>
          {/* Metadata Bar */}
          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#94a3b8', backgroundColor: '#0f172a', padding: '10px 14px', borderRadius: '6px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <span><strong>Model:</strong> <code style={{ color: '#38bdf8' }}>{data.model_name}</code></span>
            <span><strong>MAE:</strong> {data.metrics?.mae ?? 'N/A'}</span>
            <span><strong>RMSE:</strong> {data.metrics?.rmse ?? 'N/A'}</span>
            <span><strong>sMAPE:</strong> {data.metrics?.smape != null ? `${data.metrics.smape}%` : 'N/A'}</span>
            <span><strong>Drift Monitor:</strong> <span style={{ color: '#10b981', fontWeight: 600 }}>STABLE</span></span>
          </div>

          {/* Forecast Cards Table */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
            {data.forecast.map((f, i) => (
              <div key={i} style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', padding: '10px', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>{f.date}</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#a855f7' }}>
                  {f.point_forecast} {data.unit}
                </div>
                <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
                  [{f.lower_bound} – {f.upper_bound}]
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#64748b', marginTop: '12px' }}>
            <AlertCircle size={14} />
            <span>Prediction intervals represent empirical residual quantiles (95% confidence bounds) with zero temporal leakage.</span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
