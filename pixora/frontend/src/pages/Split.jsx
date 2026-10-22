import React, { useState } from 'react'
import { Upload, FileText, Scissors, Loader2, X, ChevronDown, ChevronUp } from 'lucide-react'

export default function SplitPage() {
  const [file, setFile] = useState(null)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [expanded, setExpanded] = useState({})

  const handleSplit = async () => {
    if (!file) return
    setProcessing(true); setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('tier', 'agentic')
      const res = await fetch('/api/v1/parse/split', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Split failed: ${res.status}`)
      setResult(await res.json())
    } catch (err) {
      setResult({ error: err.message })
    } finally { setProcessing(false) }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1200px]">
      <div className="mb-5">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Scissors size={24} className="text-indigo-400" /> Split Document</h2>
        <p className="text-sm text-zinc-500 mt-1">Split multi-document PDFs into logical sub-documents</p>
      </div>

      <div className="flex gap-3 mb-5">
        <div className="flex-1 border-2 border-dashed border-zinc-700 rounded-xl p-4 text-center cursor-pointer hover:border-zinc-600"
          onClick={() => document.getElementById('splitFileInput').click()}>
          <input id="splitFileInput" type="file" accept=".pdf" className="hidden" onChange={e => setFile(e.target.files[0])} />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText size={18} className="text-emerald-400" />
              <span className="text-sm font-medium">{file.name}</span>
              <button onClick={e => { e.stopPropagation(); setFile(null) }} className="ml-2 p-1 hover:bg-zinc-800 rounded"><X size={12} className="text-zinc-500" /></button>
            </div>
          ) : <span className="text-sm text-zinc-400">Drop a PDF or click to browse</span>}
        </div>
        <button onClick={handleSplit} disabled={!file || processing}
          className="px-5 py-2 rounded-lg font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 flex items-center gap-2 whitespace-nowrap">
          {processing ? <Loader2 size={16} className="animate-spin" /> : <Scissors size={16} />}
          {processing ? 'Splitting...' : 'Split'}
        </button>
      </div>

      {result?.error && (
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 mb-4">
          <span className="text-sm text-rose-400">{result.error}</span>
        </div>
      )}

      {result?.results && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-zinc-300">Found {result.total_sub_documents} sub-document{result.total_sub_documents !== 1 ? 's' : ''}</span>
          </div>
          {result.results.map((sub, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
              <button onClick={() => setExpanded(p => ({ ...p, [i]: !p[i] }))}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-zinc-800/50 transition-colors">
                <FileText size={16} className="text-indigo-400" />
                <span className="text-sm font-medium">Sub-document {sub.sub_document}</span>
                {sub.pages && <span className="text-xs text-zinc-500">Pages {sub.pages}</span>}
                {sub.doc_type && <span className="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded">{sub.doc_type}</span>}
                {sub.error && <span className="text-xs text-rose-400">{sub.error}</span>}
                <span className="ml-auto">{expanded[i] ? <ChevronUp size={14} className="text-zinc-500" /> : <ChevronDown size={14} className="text-zinc-500" />}</span>
              </button>
              {expanded[i] && sub.extraction && (
                <div className="px-4 pb-4 border-t border-zinc-800">
                  <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono bg-zinc-950 rounded-lg p-3 mt-3 max-h-[300px] overflow-auto">
                    {JSON.stringify(sub.extraction, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!result && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <Scissors size={40} className="mx-auto text-zinc-700 mb-3" />
          <p className="text-zinc-500 text-sm">Upload a multi-page PDF to detect and split logical document boundaries</p>
        </div>
      )}
    </div>
  )
}
