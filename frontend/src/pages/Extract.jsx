import React, { useState, useCallback } from 'react'
import { Upload, FileText, Play, Loader2, X, Code, Database } from 'lucide-react'
import { api } from '../api'

export default function ExtractPage() {
  const [file, setFile] = useState(null)
  const [schema, setSchema] = useState('{}')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [generatePrompt, setGeneratePrompt] = useState('')
  const [generating, setGenerating] = useState(false)

  const handleExtract = async () => {
    if (!file) return
    setProcessing(true); setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('tier', 'agentic')
      const data = await api.uploadAndParse(file, 'agentic')
      setResult(data)
    } catch (err) {
      setResult({ status: 'failed', error: err.message })
    } finally { setProcessing(false) }
  }

  const handleGenerateSchema = async () => {
    if (!generatePrompt.trim()) return
    setGenerating(true)
    try {
      const res = await fetch('/api/v1/schemas/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: generatePrompt }),
      })
      const data = await res.json()
      setSchema(JSON.stringify({ nodes: data.nodes || [] }, null, 2))
    } catch (err) {
      alert('Schema generation failed: ' + err.message)
    } finally { setGenerating(false) }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1200px]">
      <div className="mb-5">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Database size={24} className="text-indigo-400" /> Extract</h2>
        <p className="text-sm text-zinc-500 mt-1">Extract structured fields using a schema — define manually or generate with AI</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
        <div>
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Schema (JSON)</label>
          <textarea value={schema} onChange={e => setSchema(e.target.value)}
            className="w-full h-48 bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm font-mono text-zinc-300 focus:outline-none focus:border-indigo-500 resize-none" />
        </div>
        <div>
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2 block">Generate Schema with AI</label>
          <textarea value={generatePrompt} onChange={e => setGeneratePrompt(e.target.value)} placeholder="Describe the document type, e.g. 'Invoice with line items, vendor info, totals'"
            className="w-full h-32 bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500 resize-none" />
          <button onClick={handleGenerateSchema} disabled={generating || !generatePrompt.trim()}
            className="mt-2 px-4 py-2 rounded-lg text-sm font-medium bg-violet-600 hover:bg-violet-500 text-white disabled:opacity-40 flex items-center gap-2">
            {generating ? <Loader2 size={14} className="animate-spin" /> : null}
            {generating ? 'Generating...' : 'Generate Schema'}
          </button>
        </div>
      </div>

      <div className="flex gap-3 mb-5">
        <div className="flex-1 border-2 border-dashed border-zinc-700 rounded-xl p-4 text-center cursor-pointer hover:border-zinc-600"
          onClick={() => document.getElementById('extractFileInput').click()}>
          <input id="extractFileInput" type="file" className="hidden" onChange={e => setFile(e.target.files[0])} />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText size={18} className="text-emerald-400" />
              <span className="text-sm font-medium">{file.name}</span>
              <button onClick={e => { e.stopPropagation(); setFile(null) }} className="ml-2 p-1 hover:bg-zinc-800 rounded"><X size={12} className="text-zinc-500" /></button>
            </div>
          ) : <span className="text-sm text-zinc-400">Drop a document or click to browse</span>}
        </div>
        <button onClick={handleExtract} disabled={!file || processing}
          className="px-5 py-2 rounded-lg font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 flex items-center gap-2 whitespace-nowrap">
          {processing ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          {processing ? 'Extracting...' : 'Extract'}
        </button>
      </div>

      {result?.status === 'completed' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Code size={14} className="text-indigo-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Extraction Result</span>
            <span className="ml-auto text-xs text-zinc-600">{Object.keys(result.extraction || {}).filter(k => !k.startsWith('_')).length} fields</span>
          </div>
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono bg-zinc-950 rounded-lg p-3 max-h-[500px] overflow-auto">
            {JSON.stringify(result.extraction, null, 2)}
          </pre>
        </div>
      )}

      {result?.status === 'failed' && (
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4">
          <span className="text-sm text-rose-400">{result.error}</span>
        </div>
      )}
    </div>
  )
}
