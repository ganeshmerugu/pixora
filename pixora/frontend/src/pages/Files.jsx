import React, { useState, useEffect } from 'react'
import { FolderOpen, FileText, Upload, Loader2, Trash2, ExternalLink } from 'lucide-react'
import { api } from '../api'

export default function FilesPage() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listParses().then(data => { setJobs(Array.isArray(data) ? data : []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handleDelete = async (jobId) => {
    try {
      await api.deleteParse(jobId)
      setJobs(prev => prev.filter(j => j.job_id !== jobId))
    } catch {}
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1200px]">
      <div className="mb-5">
        <h2 className="text-2xl font-bold flex items-center gap-2"><FolderOpen size={24} className="text-indigo-400" /> Files</h2>
        <p className="text-sm text-zinc-500 mt-1">Browse uploaded documents and their processing results</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-zinc-500" /></div>
      ) : jobs.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <FolderOpen size={40} className="mx-auto text-zinc-700 mb-3" />
          <p className="text-zinc-500 text-sm">No files uploaded yet</p>
          <p className="text-zinc-600 text-xs mt-1">Go to Parse to upload and process documents</p>
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Filename</th>
                <th className="text-left px-4 py-3">Type</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Fields</th>
                <th className="text-left px-4 py-3">Quality</th>
                <th className="text-left px-4 py-3">Date</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.job_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-zinc-500" />
                      <span className="text-zinc-300 font-medium truncate max-w-[200px]">{job.filename || 'unknown'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded capitalize">{job.doc_type || '-'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${job.status === 'completed' ? 'text-emerald-400' : job.status === 'failed' ? 'text-rose-400' : 'text-amber-400'}`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{job.field_count || 0}</td>
                  <td className="px-4 py-3 text-zinc-400">{job.quality_score ? `${(job.quality_score * 100).toFixed(0)}%` : '-'}</td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">{job.created_at ? new Date(job.created_at).toLocaleDateString() : '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(job.job_id)} className="p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-rose-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
