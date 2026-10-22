import React, { useState, useEffect } from 'react'
import { ScrollText, DollarSign, Zap, Clock, RefreshCw, ChevronDown, ChevronRight, Download } from 'lucide-react'
import { api } from '../api'

export default function AuditLog() {
  const [tab, setTab] = useState('events')
  const [log, setLog] = useState(null)
  const [calls, setCalls] = useState(null)
  const [costs, setCosts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expandedJob, setExpandedJob] = useState(null)
  const [jobDetail, setJobDetail] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [l, s, c] = await Promise.all([
        api.getAuditLog(200),
        api.getServiceCalls(200),
        api.getCostSummary(),
      ])
      setLog(l)
      setCalls(s)
      setCosts(c)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const loadJobDetail = async (jobId) => {
    if (expandedJob === jobId) { setExpandedJob(null); return }
    setExpandedJob(jobId)
    try { setJobDetail(await api.getJobAudit(jobId)) } catch { setJobDetail(null) }
  }

  const events = log?.entries || []
  const serviceCalls = calls?.entries || []

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Audit Log</h2>
          <p className="text-sm text-zinc-500 mt-1">Pipeline events, service calls, and token costs</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Cost summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1"><Zap size={12} className="text-amber-400" /> Total Calls</div>
          <p className="text-2xl font-bold">{costs?.total_calls || 0}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1"><ScrollText size={12} className="text-indigo-400" /> Total Tokens</div>
          <p className="text-2xl font-bold">{(costs?.total_tokens || 0).toLocaleString()}</p>
          <p className="text-[11px] text-zinc-600">{(costs?.total_tokens_in || 0).toLocaleString()} in / {(costs?.total_tokens_out || 0).toLocaleString()} out</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1"><DollarSign size={12} className="text-emerald-400" /> Total Cost</div>
          <p className="text-2xl font-bold">${(costs?.total_cost_usd || 0).toFixed(4)}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1"><Clock size={12} className="text-sky-400" /> Events Logged</div>
          <p className="text-2xl font-bold">{log?.total || 0}</p>
        </div>
      </div>

      {/* Cost by operation */}
      {costs?.by_operation && Object.keys(costs.by_operation).length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-6">
          <h3 className="text-sm font-medium mb-3">Cost by Operation</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-zinc-500 uppercase tracking-wider border-b border-zinc-800">
                <th className="text-left pb-2 font-medium">Operation</th>
                <th className="text-right pb-2 font-medium">Calls</th>
                <th className="text-right pb-2 font-medium">Tokens</th>
                <th className="text-right pb-2 font-medium">Avg Duration</th>
                <th className="text-right pb-2 font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(costs.by_operation).map(([op, m]) => (
                <tr key={op} className="border-b border-zinc-800/50">
                  <td className="py-2 font-medium">{op}</td>
                  <td className="py-2 text-right text-zinc-400">{m.calls}</td>
                  <td className="py-2 text-right text-zinc-400">{m.tokens.toLocaleString()}</td>
                  <td className="py-2 text-right text-zinc-400">{m.avg_duration_ms}ms</td>
                  <td className="py-2 text-right text-zinc-300">${m.cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab switch */}
      <div className="flex gap-1 mb-4">
        {['events', 'service_calls'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium rounded-lg ${
              tab === t ? 'bg-indigo-500/10 text-indigo-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
            }`}>
            {t === 'events' ? 'Pipeline Events' : 'Service Calls'}
          </button>
        ))}
      </div>

      {/* Event log table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        {(tab === 'events' ? events : serviceCalls).length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-12">No {tab === 'events' ? 'events' : 'service calls'} yet. Parse a document to see logs.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 uppercase tracking-wider border-b border-zinc-800">
                  <th className="text-left p-3 font-medium">Time</th>
                  <th className="text-left p-3 font-medium">{tab === 'events' ? 'Event' : 'Service'}</th>
                  <th className="text-left p-3 font-medium">{tab === 'events' ? 'Agent' : 'Operation'}</th>
                  <th className="text-left p-3 font-medium">Detail</th>
                  <th className="text-right p-3 font-medium">Duration</th>
                  <th className="text-right p-3 font-medium">Tokens</th>
                  <th className="text-right p-3 font-medium">Export</th>
                </tr>
              </thead>
              <tbody>
                {(tab === 'events' ? events : serviceCalls).map((e, i) => (
                  <tr key={e.id || i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="p-3 text-zinc-500 font-mono whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="p-3">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        (e.event_type || '').includes('complete') ? 'bg-emerald-500/10 text-emerald-400' :
                        (e.event_type || '').includes('start') ? 'bg-sky-500/10 text-sky-400' :
                        (e.status === 'error' || (e.event_type || '').includes('fail')) ? 'bg-rose-500/10 text-rose-400' :
                        'bg-zinc-800 text-zinc-400'
                      }`}>
                        {e.event_type || e.service || '-'}
                      </span>
                    </td>
                    <td className="p-3 text-zinc-300">{e.agent || e.operation || '-'}</td>
                    <td className="p-3 text-zinc-400 max-w-xs truncate">{e.detail || '-'}</td>
                    <td className="p-3 text-right text-zinc-400">{e.duration_ms || 0}ms</td>
                    <td className="p-3 text-right text-zinc-400">
                      {(e.tokens_in || 0) + (e.tokens_out || 0) > 0
                        ? `${((e.tokens_in || 0) + (e.tokens_out || 0)).toLocaleString()}`
                        : '-'}
                    </td>
                    <td className="p-3 text-right">
                      {e.job_id && (e.event_type || '').includes('complete') && (
                        <a href={api.exportAudit(e.job_id, 'json')} download
                          className="inline-flex items-center gap-1 px-2 py-1 text-[10px] bg-indigo-500/10 text-indigo-400 rounded hover:bg-indigo-500/20 transition-colors"
                          title="Download compliance audit package">
                          <Download size={10} /> Audit
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
