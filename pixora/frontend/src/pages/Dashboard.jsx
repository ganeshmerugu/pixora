import React, { useState, useEffect } from 'react'
import { FileText, Clock, CheckCircle, AlertTriangle, Shield, Zap, RefreshCw, Target, Eye, BarChart3 } from 'lucide-react'
import { api } from '../api'

function StatCard({ icon: Icon, label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo: 'bg-indigo-500/10 text-indigo-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    amber: 'bg-amber-500/10 text-amber-400',
    rose: 'bg-rose-500/10 text-rose-400',
    sky: 'bg-sky-500/10 text-sky-400',
  }
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-zinc-500 uppercase tracking-wider font-medium">{label}</span>
        <div className={`p-2 rounded-lg ${colors[color]}`}><Icon size={16} /></div>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </div>
  )
}

function MetricBar({ label, value, color = 'indigo' }) {
  const pct = Math.round(value * 100)
  const barColor = pct >= 90 ? 'bg-emerald-500' : pct >= 75 ? 'bg-indigo-500' : pct >= 60 ? 'bg-amber-500' : 'bg-rose-500'
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-zinc-400">{label}</span>
        <span className="text-zinc-300 font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [healthy, setHealthy] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadStats = () => {
    setLoading(true)
    api.getDashboardStats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    api.health().then(() => setHealthy(true)).catch(() => setHealthy(false))
    loadStats()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await api.refreshDashboardStats()
      await loadStats()
    } finally {
      setRefreshing(false)
    }
  }

  const b = stats?.benchmarks || {}
  const jobs = stats?.jobs || {}
  const byType = b.by_doc_type || {}

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Dashboard</h2>
          <p className="text-sm text-zinc-500 mt-1">
            {b.total_documents ? `Real metrics from ${b.total_documents} golden benchmarks` : 'Loading pipeline metrics...'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleRefresh} disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-xs text-zinc-400 disabled:opacity-50">
            <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Running pipeline...' : 'Re-run Benchmarks'}
          </button>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${healthy ? 'bg-emerald-400' : healthy === false ? 'bg-rose-400' : 'bg-zinc-600'}`} />
            <span className="text-xs text-zinc-500">{healthy ? 'API Connected' : healthy === false ? 'API Offline' : 'Checking...'}</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 text-zinc-500 text-sm">
          <RefreshCw size={24} className="mx-auto animate-spin mb-3 text-indigo-400" />
          Running documents through real pipeline...
        </div>
      ) : (
        <>
          {/* Job stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={FileText} label="Total Jobs" value={jobs.total || 0} sub="All time" color="indigo" />
            <StatCard icon={CheckCircle} label="Completed" value={jobs.completed || 0} sub="Successfully processed" color="emerald" />
            <StatCard icon={Clock} label="In Queue" value={jobs.queued || 0} sub="Awaiting processing" color="amber" />
            <StatCard icon={AlertTriangle} label="Failed" value={jobs.failed || 0} sub="Needs attention" color="rose" />
          </div>

          {/* Benchmark pipeline metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={Target} label="Pass Rate" value={`${Math.round((b.pass_rate || 0) * 100)}%`}
              sub={`${b.accept_count || 0} accepted, ${b.review_count || 0} review, ${b.reprocess_count || 0} reprocess`} color="emerald" />
            <StatCard icon={Shield} label="Grounding" value={`${Math.round((b.avg_grounding_rate || 0) * 100)}%`}
              sub={`${b.hallucination_count || 0} hallucinations flagged`} color="indigo" />
            <StatCard icon={BarChart3} label="Avg F1" value={`${Math.round((b.avg_f1 || 0) * 100)}%`}
              sub={`Exact match: ${Math.round((b.avg_exact_match || 0) * 100)}%`} color="sky" />
            <StatCard icon={Zap} label="Avg Time" value={`${b.avg_processing_ms || 0}ms`}
              sub={`${b.total_documents || 0} documents processed`} color="amber" />
          </div>

          {/* Quality dimensions from real pipeline */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
                <Shield size={14} className="text-indigo-400" /> Quality Dimensions
                <span className="text-[10px] text-zinc-600 ml-auto">from real pipeline</span>
              </h3>
              <div className="space-y-3">
                <MetricBar label="Grounding Rate (anti-hallucination)" value={b.avg_grounding_rate || 0} />
                <MetricBar label="Extraction Accuracy" value={b.avg_accuracy || 0} />
                <MetricBar label="Completeness" value={b.avg_completeness || 0} />
                <MetricBar label="Layout Fidelity" value={b.avg_layout_fidelity || 0} />
                <MetricBar label="F1 Score" value={b.avg_f1 || 0} />
                <MetricBar label="Exact Match Rate" value={b.avg_exact_match || 0} />
              </div>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
              <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
                <Eye size={14} className="text-emerald-400" /> Performance by Document Type
              </h3>
              {Object.keys(byType).length === 0 ? (
                <p className="text-sm text-zinc-600 text-center py-4">No benchmark data yet</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(byType).map(([dt, m]) => (
                    <div key={dt} className="px-3 py-3 bg-zinc-800/50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium capitalize">{dt}</span>
                          <span className="text-[10px] text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">{m.count} doc{m.count !== 1 ? 's' : ''}</span>
                        </div>
                        <span className={`text-xs font-medium ${m.pass_rate >= 0.8 ? 'text-emerald-400' : m.pass_rate >= 0.5 ? 'text-amber-400' : 'text-rose-400'}`}>
                          {Math.round(m.pass_rate * 100)}% pass
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-[11px]">
                        <div>
                          <span className="text-zinc-500">Quality</span>
                          <p className="text-zinc-300 font-medium">{Math.round(m.avg_quality * 100)}%</p>
                        </div>
                        <div>
                          <span className="text-zinc-500">Grounding</span>
                          <p className="text-zinc-300 font-medium">{Math.round(m.avg_grounding * 100)}%</p>
                        </div>
                        <div>
                          <span className="text-zinc-500">F1</span>
                          <p className="text-zinc-300 font-medium">{Math.round(m.avg_f1 * 100)}%</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Per-document benchmark results */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
            <h3 className="text-sm font-medium mb-4">Benchmark Results (per document)</h3>
            {(b.results || []).length === 0 ? (
              <p className="text-sm text-zinc-500 text-center py-8">No benchmark results yet. Click "Re-run Benchmarks".</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800">
                      <th className="text-left pb-2 font-medium">Document</th>
                      <th className="text-left pb-2 font-medium">Type</th>
                      <th className="text-left pb-2 font-medium">Quality</th>
                      <th className="text-left pb-2 font-medium">Grounding</th>
                      <th className="text-left pb-2 font-medium">F1</th>
                      <th className="text-left pb-2 font-medium">Rounds</th>
                      <th className="text-left pb-2 font-medium">Time</th>
                      <th className="text-left pb-2 font-medium">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(b.results || []).map(r => {
                      const q = r.quality_report || {}
                      const g = r.grounding_report || {}
                      const m = r.metrics || r.eval_metrics || {}
                      const s = r.score || r.eval_score || {}
                      return (
                        <tr key={r.document_id} className="border-b border-zinc-800/50">
                          <td className="py-2.5 font-mono text-xs text-zinc-400">{r.document_id}</td>
                          <td className="py-2.5">
                            <span className="px-1.5 py-0.5 bg-zinc-800 rounded text-[11px] capitalize">{r.doc_type}</span>
                          </td>
                          <td className="py-2.5 text-zinc-300">{Math.round((q.overall_score || 0) * 100)}%</td>
                          <td className="py-2.5 text-zinc-300">{Math.round((g.grounding_rate || 0) * 100)}%</td>
                          <td className="py-2.5 text-zinc-300">{Math.round((m.f1 || 0) * 100)}%</td>
                          <td className="py-2.5 text-zinc-400">{r.correction_rounds}</td>
                          <td className="py-2.5 text-zinc-400">{r.processing_time_ms}ms</td>
                          <td className="py-2.5">
                            <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                              s.passed ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                            }`}>
                              {s.passed ? 'PASS' : 'FAIL'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
