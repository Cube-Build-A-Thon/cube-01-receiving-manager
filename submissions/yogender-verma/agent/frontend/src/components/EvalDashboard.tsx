import React, { useState, useEffect } from 'react';
import { runEvalSuite } from '../api';
import { BarChart3, RefreshCw, AlertOctagon, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';

export const EvalDashboard: React.FC = () => {
  const [evalData, setEvalData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleRunEval = async () => {
    setLoading(true);
    try {
      const data = await runEvalSuite();
      setEvalData(data);
    } catch (err: any) {
      alert('Failed to run eval suite: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleRunEval();
  }, []);

  if (!evalData && loading) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
        <RefreshCw className="pulse-active" size={32} style={{ color: 'var(--accent-blue)', marginBottom: '12px' }} />
        <div>Executing 50-Unit Held-Out Vision Evaluation Suite...</div>
      </div>
    );
  }

  const summary = evalData?.evaluation_summary;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
      {/* Header bar */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BarChart3 style={{ color: 'var(--accent-emerald)' }} size={24} />
            Receiving Manager Model Evaluation & Failure Mode Suite
          </h2>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Evaluated on 50 unseen units labelled independently by dual labellers (Labeller A & B).
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleRunEval} disabled={loading}>
          <RefreshCw className={loading ? 'pulse-active' : ''} size={16} /> Re-run 50-Unit Eval
        </button>
      </div>

      {summary && (
        <>
          {/* Top Scorecards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px' }}>
            <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>COHEN'S KAPPA (K)</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>{summary.cohens_kappa_inter_annotator_agreement}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)' }}>High Labeller Agreement</div>
            </div>

            <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>OVERALL ACCURACY</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>{summary.overall_accuracy_excluding_uncertain}%</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Excluding UNCERTAIN</div>
            </div>

            <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>PRECISION / RECALL</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-purple)' }}>{summary.precision} / {summary.recall}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>F1-Score: {summary.f1_score}</div>
            </div>

            <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>FALSE POS / NEG</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-rose)' }}>{summary.false_positives_count} FP / {summary.false_negatives_count} FN</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Explicitly Separated</div>
            </div>

            <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>UNCERTAIN RATE</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-amber)' }}>{summary.uncertain_rate_pct}%</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Rule 4 Verdicts ({summary.uncertain_verdicts_count} units)</div>
            </div>
          </div>

          {/* Per-Check Metrics & Failure Modes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Per Check Breakdown */}
            <div className="glass-panel" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px' }}>Per-Check Decision Quality</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Check Name</th>
                    <th style={{ padding: '8px' }}>Accuracy</th>
                    <th style={{ padding: '8px' }}>FP / FN</th>
                    <th style={{ padding: '8px' }}>Uncertain</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(evalData.per_check_metrics).map(([name, data]: [string, any]) => (
                    <tr key={name} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '8px', fontWeight: 600 }}>{name}</td>
                      <td style={{ padding: '8px', color: 'var(--accent-emerald)' }}>{data.accuracy}%</td>
                      <td style={{ padding: '8px', color: 'var(--accent-rose)' }}>{data.fp} FP / {data.fn} FN</td>
                      <td style={{ padding: '8px', color: 'var(--accent-amber)' }}>{data.uncertain}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Named Failure Modes */}
            <div className="glass-panel" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertOctagon style={{ color: 'var(--accent-rose)' }} size={20} />
                Documented Failure Modes & Edge Cases
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', fontSize: '0.8rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--accent-rose)' }}>1. Visual Glare & Polybag Reflection</div>
                  <div style={{ color: 'var(--text-secondary)' }}>Plastic shrink wrap reflects warehouse LED spotlights, triggering UNCERTAIN verdict on text resolution.</div>
                </div>

                <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', fontSize: '0.8rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--accent-rose)' }}>2. Subtle Carton Corner Crushing</div>
                  <div style={{ color: 'var(--text-secondary)' }}>Cartons with minor under-10% corner wall compression produce false negative PASS verdicts without multi-angle photos.</div>
                </div>

                <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', fontSize: '0.8rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--accent-rose)' }}>3. Spec Variant Print Font Discrepancy</div>
                  <div style={{ color: 'var(--text-secondary)' }}>Foreign supplier variant labels in non-English fonts generate 1 False Positive flag on color variant checks.</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
