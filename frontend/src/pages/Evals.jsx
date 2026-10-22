import React, { useState, useEffect } from 'react'
import { Play, BarChart3, TrendingDown, TrendingUp, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react'
import { api } from '../api'

export default function EvalsPage() {
  const [reports, setReports] = useState([])
  const [drift, setDrift] = useState([])
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState(null)

  const load = () => {
    api.listReports().then(setReports).catch(() => {})
    api.getDrift().then(setDrift).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const handleRun = async () => {
    setRunning(true)
    try {
      const report = await api.runSuite({ suite_name: 'golden-100' })
      setSelected(report)
      load()
    } finally {
      setRunning(false)
    }
  }

  const pct = (v) => v != null ? `${Math.round(v * 100)}%` : '--'

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Evaluations</h2>
          <p className="text-sm text-zinc-500 mt-1">Run golden benchmarks and track regressions</p>
        </div>
        <button onClick={handleRun} disabled={running}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors">
          {running ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? 'Running 100 benchmarks...' : 'Run Suite'}
        </button>
      </div>

      {selected && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            {selected.pass_rate >= 1.0 ? <CheckCircle size={18} className="text-emerald-400" /> : <AlertTriangle size={18} className="text-amber-400" />}
            <h3 className="font-medium">Latest Run: {selected.suite_name}</h3>
            <span className="text-xs text-zinc-500 ml-auto">{selected.total_cases} benchmarks</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-emerald-400">{pct(selected.pass_rate)}</p>
              <p className="text-xs text-zinc-500">Pass Rate</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold">{pct(selected.avg_f1)}</p>
              <p className="text-xs text-zinc-500">Avg F1</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold">{pct(selected.avg_quality)}</p>
              <p className="text-xs text-zinc-500">Avg Quality</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-emerald-400">{selected.passed}</p>
              <p className="text-xs text-zinc-500">Passed / {selected.total_cases}</p>
            </div>
          </div>

          {selected.by_doc_type && Object.keys(selected.by_doc_type).length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wider mb-3">By Document Type</p>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {Object.entries(selected.by_doc_type).sort().map(([dt, info]) => (
                  <div key={dt} className="bg-zinc-800/30 rounded-lg p-2 text-center">
                    <p className="text-xs font-medium text-zinc-300">{dt.replace(/_/g, ' ')}</p>
                    <p className="text-lg font-bold mt-1">{pct(info.avg_quality)}</p>
                    <p className="text-[10px] text-zinc-500">F1: {pct(info.avg_f1)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4 flex items-center gap-2"><BarChart3 size={14} className="text-indigo-400" /> Run History</h3>
          {reports.length === 0 ? (
            <p className="text-xs text-zinc-600 text-center py-6">No runs yet — click Run Suite</p>
          ) : (
            <div className="space-y-2">
              {reports.map(r => (
                <div key={r.id} onClick={() => setSelected(r)}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                    selected?.id === r.id ? 'bg-indigo-500/10 border border-indigo-500/20' : 'bg-zinc-800/30 hover:bg-zinc-800/50'
                  }`}>
                  <div>
                    <p className="text-xs font-medium">{r.suite_name}</p>
                    <p className="text-[10px] text-zinc-500">{r.total_cases} cases</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold ${r.pass_rate >= 1.0 ? 'text-emerald-400' : 'text-amber-400'}`}>{pct(r.pass_rate)}</p>
                    <p className="text-[10px] text-zinc-500">F1: {pct(r.avg_f1)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
            {drift.some(d => d.regression) ? <TrendingDown size={14} className="text-rose-400" /> : <TrendingUp size={14} className="text-emerald-400" />}
            Drift Detection
          </h3>
          {drift.length === 0 ? (
            <p className="text-xs text-zinc-600 text-center py-6">Run the suite twice to see drift analysis</p>
          ) : (
            <div className="space-y-3">
              {drift.map((d, i) => (
                <div key={i} className={`p-3 rounded-lg ${d.regression ? 'bg-rose-500/5 border border-rose-500/20' : 'bg-zinc-800/30'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-zinc-500">{d.from_report?.slice(0, 8)} &rarr; {d.to_report?.slice(0, 8)}</span>
                    {d.regression ? (
                      <span className="px-2 py-0.5 bg-rose-500/10 text-rose-400 rounded text-[10px] font-medium">REGRESSION</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-medium">STABLE</span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div><span className="text-zinc-500">Quality </span><span className={d.quality_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{d.quality_delta >= 0 ? '+' : ''}{(d.quality_delta * 100).toFixed(1)}%</span></div>
                    <div><span className="text-zinc-500">F1 </span><span className={d.f1_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{d.f1_delta >= 0 ? '+' : ''}{(d.f1_delta * 100).toFixed(1)}%</span></div>
                    <div><span className="text-zinc-500">Pass </span><span className={d.pass_rate_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{d.pass_rate_delta >= 0 ? '+' : ''}{(d.pass_rate_delta * 100).toFixed(1)}%</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
