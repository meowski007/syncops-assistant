import React from 'react';
import { KPIsResponse } from '../api';
import { Activity, CheckCircle2, Clock, RotateCcw, MessageSquare, HelpCircle, Users } from 'lucide-react';

interface Props {
  kpis: KPIsResponse | null;
  loading: boolean;
}

export const KPICards: React.FC<Props> = ({ kpis, loading }) => {
  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>Loading Reliability KPIs...</div>;
  }
  if (!kpis) return null;

  const cards = [
    {
      title: 'Sync Success Rate',
      value: `${kpis.sync_success_rate.value}%`,
      unit: '%',
      sample: `Sample: ${kpis.sync_success_rate.sample_size}`,
      delta: `${(kpis.sync_success_rate.value - 95.0).toFixed(1)}% vs SLO`,
      isGood: kpis.sync_success_rate.value >= 95.0,
      icon: <CheckCircle2 size={20} color="#10b981" />,
      desc: kpis.sync_success_rate.description,
    },
    {
      title: 'Recovery Rate',
      value: `${kpis.recovery_rate.value}%`,
      unit: '%',
      sample: `${kpis.recovery_rate.sample_size} Incidents`,
      delta: 'Mitigation Efficacy',
      isGood: kpis.recovery_rate.value >= 75.0,
      icon: <Activity size={20} color="#38bdf8" />,
      desc: kpis.recovery_rate.description,
    },
    {
      title: 'Time to Recover (MTTR)',
      value: `${kpis.time_to_recover.value}m`,
      unit: 'min',
      sample: `${kpis.time_to_recover.sample_size} Resolved`,
      delta: 'Target < 60m',
      isGood: kpis.time_to_recover.value <= 60.0,
      icon: <Clock size={20} color="#fbbf24" />,
      desc: kpis.time_to_recover.description,
    },
    {
      title: 'Repeat Failure Rate',
      value: `${kpis.repeat_failure_rate.value}%`,
      unit: '%',
      sample: `${kpis.repeat_failure_rate.sample_size} Impacted`,
      delta: kpis.repeat_failure_rate.value <= 5.0 ? 'Nominal' : 'Elevated',
      isGood: kpis.repeat_failure_rate.value <= 5.0,
      icon: <RotateCcw size={20} color={kpis.repeat_failure_rate.value <= 5.0 ? '#10b981' : '#f87171'} />,
      desc: kpis.repeat_failure_rate.description,
    },
    {
      title: 'Support Tickets',
      value: `${kpis.sync_related_support_tickets.value}`,
      unit: 'tickets',
      sample: `${kpis.sync_related_support_tickets.ticket_to_failure_ratio}% ratio`,
      delta: 'Escalation Volume',
      isGood: true,
      icon: <MessageSquare size={20} color="#a78bfa" />,
      desc: kpis.sync_related_support_tickets.description,
    },
    {
      title: 'Self-Service Rate',
      value: `${kpis.self_service_resolution_rate.value}%`,
      unit: '%',
      sample: `${kpis.self_service_resolution_rate.sample_size} Tickets`,
      delta: 'Customer Self-Help',
      isGood: kpis.self_service_resolution_rate.value >= 30.0,
      icon: <HelpCircle size={20} color="#34d399" />,
      desc: kpis.self_service_resolution_rate.description,
    },
    {
      title: 'Sync Feature Adoption',
      value: `${kpis.adoption_rate.value}%`,
      unit: '% DAU',
      sample: 'Active Users',
      delta: 'Adoption Trend',
      isGood: kpis.adoption_rate.value >= 70.0,
      icon: <Users size={20} color="#60a5fa" />,
      desc: kpis.adoption_rate.description,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px', marginBottom: '24px' }}>
      {cards.map((c, i) => (
        <div key={i} style={{ backgroundColor: '#1e293b', padding: '16px', borderRadius: '10px', border: '1px solid #334155' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>{c.title}</span>
            {c.icon}
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>{c.value}</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
            <span>{c.sample}</span>
            <span style={{ color: c.isGood ? '#10b981' : '#f87171', fontWeight: 600 }}>{c.delta}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
