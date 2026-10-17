import React, { useState, useEffect } from 'react'
import { RefreshCw, Trash2, XCircle, Eye, ChevronRight, Shield, TrendingUp, FileText, Zap, RotateCcw, Download, Image, Loader2, Link2 } from 'lucide-react'
import { api } from '../api'

const STATUS_STYLES = {
  completed: 'bg-emerald-500/10 text-emerald-400',
  queued: 'bg-amber-500/10 text-amber-400',
  processing: 'bg-sky-500/10 text-sky-400',
  failed: 'bg-rose-500/10 text-rose-400',
  cancelled: 'bg-zinc-800 text-zinc-500',
}

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [rerunning, setRerunning] = useState(null)

  const load = () => {
    setLoading(true)
    api.listParses().then(setJobs).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSelect = async (j) => {
    setSelected(j)
    if (j.job_id && j.status === 'completed') {
      try { setDetail(await api.getParse(j.job_id)) } catch { setDetail(null) }
    } else {
      setDetail(null)
    }
  }

  const handleRerun = async (job, tier) => {
    setRerunning(job.job_id)
    try {
      const result = await api.rerunJob(job.job_id, tier)
      load()
      if (result.job_id) handleSelect({ ...result, job_id: result.job_id })
    } catch {} finally { setRerunning(null) }
  }

  const isImageFile = (fn) => /\.(png|jpg|jpeg|webp|gif|bmp|tiff?|heic|heif|avif|svg)$/i.test(fn || '')

  const handleCancel = async (id) => { await api.cancelParse(id); load() }
  const handleDelete = async (id) => {
    await api.deleteParse(id)
    if (selected?.job_id === id) { setSelected(null); setDetail(null) }
    load()
  }

  const qualityPct = (v) => v ? `${Math.round(v * 100)}%` : '--'

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Jobs</h2>
          <p className="text-sm text-zinc-500 mt-1">{jobs.length} total jobs</p>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 transition-colors">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="col-span-1 lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          {jobs.length === 0 ? (
            <p className="text-sm text-zinc-500 text-center py-12">No jobs yet — upload a document to get started</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800">
                  <th className="text-left p-3 font-medium">File</th>
                  <th className="text-left p-3 font-medium">Type</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Quality</th>
                  <th className="text-left p-3 font-medium">Fields</th>
                  <th className="text-right p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.job_id} className={`border-b border-zinc-800/50 cursor-pointer transition-colors ${
                    selected?.job_id === j.job_id ? 'bg-indigo-500/5' : 'hover:bg-zinc-800/50'
                  }`} onClick={() => handleSelect(j)}>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <FileText size={14} className="text-zinc-600 flex-shrink-0" />
                        <span className="text-zinc-300 text-xs truncate max-w-[160px]">{j.filename || j.job_id?.slice(0, 12)}</span>
                      </div>
                    </td>
                    <td className="p-3">
                      {j.doc_type ? (
                        <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded text-[11px]">{j.doc_type}</span>
                      ) : <span className="text-zinc-600 text-xs">--</span>}
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[j.status] || STATUS_STYLES.queued}`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="p-3 text-xs">
                      {j.quality_score > 0 ? (
                        <span className={j.quality_score >= 0.8 ? 'text-emerald-400' : j.quality_score >= 0.6 ? 'text-amber-400' : 'text-rose-400'}>
                          {qualityPct(j.quality_score)}
                        </span>
                      ) : <span className="text-zinc-600">--</span>}
                    </td>
                    <td className="p-3 text-xs text-zinc-400">{j.field_count || '--'}</td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {j.status === 'completed' && (
                          <button onClick={(e) => { e.stopPropagation(); handleRerun(j) }}
                            disabled={rerunning === j.job_id}
                            className="p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-emerald-400 disabled:opacity-40" title="Rerun">
                            {rerunning === j.job_id ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
                          </button>
                        )}
                        {j.status === 'queued' && (
                          <button onClick={(e) => { e.stopPropagation(); handleCancel(j.job_id) }}
                            className="p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-amber-400" title="Cancel">
                            <XCircle size={14} />
                          </button>
                        )}
                        <a href={api.getJobFileUrl(j.job_id)} target="_blank" rel="noopener"
                          onClick={e => e.stopPropagation()}
                          className="p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-indigo-400" title="View file">
                          <Download size={14} />
                        </a>
                        <button onClick={(e) => { e.stopPropagation(); handleDelete(j.job_id) }}
                          className="p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-rose-400" title="Delete">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          {selected ? (
            <div className="space-y-4">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <Eye size={14} className="text-indigo-400" /> Job Detail
              </h3>

              {/* File preview */}
              {selected.job_id && (
                <div className="rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950">
                  {isImageFile(selected.filename) ? (
                    <img src={api.getJobFileUrl(selected.job_id)} alt={selected.filename}
                      className="w-full max-h-48 object-contain bg-white" />
                  ) : (
                    <div className="p-4 text-center">
                      <FileText size={28} className="mx-auto text-zinc-600 mb-1" />
                      <p className="text-[10px] text-zinc-500">{selected.filename}</p>
                    </div>
                  )}
                  <div className="flex border-t border-zinc-800">
                    <a href={api.getJobFileUrl(selected.job_id)} target="_blank" rel="noopener"
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] text-zinc-400 hover:text-indigo-400 hover:bg-zinc-800 transition-colors">
                      <Download size={10} /> Download
                    </a>
                    <button onClick={() => handleRerun(selected)} disabled={rerunning === selected.job_id}
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] text-zinc-400 hover:text-emerald-400 hover:bg-zinc-800 transition-colors border-l border-zinc-800 disabled:opacity-40">
                      {rerunning === selected.job_id ? <Loader2 size={10} className="animate-spin" /> : <RotateCcw size={10} />}
                      Rerun
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-zinc-500">File</span><span className="text-zinc-300 truncate max-w-[140px]">{selected.filename || '--'}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Type</span><span className="text-zinc-300">{selected.doc_type || '--'}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Tier</span><span className="text-zinc-300">{selected.tier || '--'}</span></div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Status</span>
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[selected.status]}`}>{selected.status}</span>
                </div>
                <div className="flex justify-between"><span className="text-zinc-500">Quality</span><span className="text-zinc-300">{qualityPct(selected.quality_score)}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Fields</span><span className="text-zinc-300">{selected.field_count || 0}</span></div>
                {selected.parent_job_id && (
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-500">Rerun of</span>
                    <button onClick={() => { const parent = jobs.find(j => j.job_id === selected.parent_job_id); if (parent) handleSelect(parent) }}
                      className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-[10px]">
                      <Link2 size={9} />{selected.parent_job_id.slice(0, 10)}...
                    </button>
                  </div>
                )}
                {selected.created_at && <div className="flex justify-between"><span className="text-zinc-500">Created</span><span className="text-zinc-300">{new Date(selected.created_at).toLocaleString()}</span></div>}
                {selected.error && <div className="text-rose-400 text-xs mt-2 p-2 bg-rose-500/5 rounded">{selected.error}</div>}
              </div>

              {detail?.extraction && (
                <div className="pt-3 border-t border-zinc-800">
                  <p className="text-xs text-zinc-500 mb-2">Extracted Fields</p>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {Object.entries(detail.extraction).filter(([k]) => !k.startsWith('_')).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs py-1 border-b border-zinc-800/30">
                        <span className="text-zinc-500 truncate max-w-[100px]">{k.replace(/_/g, ' ')}</span>
                        <span className="text-zinc-300 truncate max-w-[120px] text-right">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {detail?.quality_report && (
                <div className="pt-3 border-t border-zinc-800 space-y-1 text-xs">
                  <p className="text-zinc-500 mb-1">Quality Breakdown</p>
                  {['completeness', 'accuracy_confidence', 'grounding_score', 'layout_fidelity'].map(k => {
                    const v = detail.quality_report[k]
                    return v != null ? (
                      <div key={k} className="flex justify-between">
                        <span className="text-zinc-500">{k.replace(/_/g, ' ')}</span>
                        <span className="text-zinc-300">{qualityPct(v)}</span>
                      </div>
                    ) : null
                  })}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-zinc-600 text-center py-8">Select a job to view details</p>
          )}
        </div>
      </div>
    </div>
  )
}
