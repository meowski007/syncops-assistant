import React, { useState, useEffect } from 'react';
import { api, KPIsResponse, Incident } from './api';
import { KPICards } from './components/KPICards';
import { IncidentTable } from './components/IncidentTable';
import { ForecastChart } from './components/ForecastChart';
import { DataQualityPanel } from './components/DataQualityPanel';
import { TriageChat } from './components/TriageChat';
import { RefreshCw, Shield, Layers, Radio } from 'lucide-react';
import './App.css';

export const App: React.FC = () => {
  const [kpis, setKpis] = useState<KPIsResponse | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      const [kpiRes, incRes] = await Promise.all([
        api.getKPIs(),
        api.getIncidents(),
      ]);
      setKpis(kpiRes);
      setIncidents(incRes);
      if (incRes.length > 0 && !selectedIncident) {
        setSelectedIncident(incRes[0]);
      }
    } catch (err) {
      console.error('Failed to load operational telemetry:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="header">
        <div className="header-brand">
          <div className="logo-badge">
            <Radio size={20} color="#38bdf8" />
          </div>
          <div>
            <h1 className="header-title">SyncOps Assistant</h1>
            <p className="header-subtitle">
              Customer-Experience Reliability Platform & Autonomous SRE
            </p>
          </div>
        </div>

        <div className="header-actions">
          <div className="badge badge-live">
            <span className="live-dot" />
            LIVE TELEMETRY
          </div>
          <div className="badge badge-version">v2.0 AI & DATA UPGRADE</div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="refresh-btn"
            title="Refresh Telemetry"
          >
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* KPI Strip */}
        <section className="section">
          <KPICards kpis={kpis} loading={loading} />
        </section>

        {/* Data Governance & Quality Strip */}
        <section className="section">
          <DataQualityPanel />
        </section>

        {/* Two-Column SRE Operations Layout */}
        <div className="operations-grid">
          {/* Left Column: Incidents & Forecasts */}
          <div className="col-left">
            <IncidentTable
              incidents={incidents}
              loading={loading}
              selectedId={selectedIncident?.id || null}
              onSelectIncident={(inc) => setSelectedIncident(inc)}
            />
            <ForecastChart />
          </div>

          {/* Right Column: RAG Triage Assistant */}
          <div className="col-right">
            <TriageChat selectedIncident={selectedIncident} />

            {/* Quick SRE Reference Card */}
            <div className="card guide-card">
              <div className="card-header-sm">
                <Layers size={16} color="#38bdf8" />
                <h4 style={{ margin: 0, fontSize: '14px', color: '#f8fafc' }}>
                  Architecture & Lineage Guide
                </h4>
              </div>
              <ul className="guide-list">
                <li>
                  <strong>Raw Event Staging:</strong> SQLite table <code>raw_sync_events</code> receives external telemetry with idempotency keys.
                </li>
                <li>
                  <strong>Data Governance Layer:</strong> Validates 5 core schema constraints, quarantines malformed records, and enforces HMAC-SHA256 masking on customer identifiers.
                </li>
                <li>
                  <strong>Clean Analytical Store:</strong> Normalized <code>clean_sync_events</code> table powers the 7 core reliability KPIs.
                </li>
                <li>
                  <strong>Time-Series Engine:</strong> Walk-forward Holt-Winters exponential smoothing and naive baselines predict failure rates.
                </li>
                <li>
                  <strong>Grounded RAG Triage:</strong> Sublinear TF-IDF + Cosine retriever grounds triage recommendations with strict section citations and low-relevance refusal guardrails.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div>
            <strong>SyncOps Assistant</strong> — Apple Services Engineering SRE Portfolio Project
          </div>
          <div className="footer-synthetic">
            <span>Synthetic Telemetry: 5,000 Sync Events | 300 Devices</span>
            <span>All metrics and incident runbooks are synthetic for interview demonstration.</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
