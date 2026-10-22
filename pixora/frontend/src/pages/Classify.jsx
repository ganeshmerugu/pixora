import React, { useState } from 'react'
import { Upload, FileText, Tag, Loader2, X, CheckCircle } from 'lucide-react'
import { api } from '../api'

export default function ClassifyPage() {
  const [file, setFile] = useState(null)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)

  const handleClassify = async () => {
    if (!file) return
    setProcessing(true); setResult(null)
    try {
      const data = await api.uploadAndParse(file, 'fast')
      setResult({
        doc_type: data.doc_type,
        confidence: data.quality_report?.accuracy_confidence || 0.85,
        fields_found: Object.keys(data.extraction || {}).filter(k => !k.startsWith('_')).length,
      })
    } catch (err) {
      setResult({ error: err.message })
    } finally { setProcessing(false) }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1200px]">
      <div className="mb-5">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Tag size={24} className="text-indigo-400" /> Classify</h2>
        <p className="text-sm text-zinc-500 mt-1">Automatically detect document type using hybrid rule + vision classification</p>
      </div>

      <div className="flex gap-3 mb-5">
        <div className="flex-1 border-2 border-dashed border-zinc-700 rounded-xl p-4 text-center cursor-pointer hover:border-zinc-600"
          onClick={() => document.getElementById('classifyFileInput').click()}>
          <input id="classifyFileInput" type="file" className="hidden" onChange={e => setFile(e.target.files[0])} />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText size={18} className="text-emerald-400" />
              <span className="text-sm font-medium">{file.name}</span>
              <button onClick={e => { e.stopPropagation(); setFile(null) }} className="ml-2 p-1 hover:bg-zinc-800 rounded"><X size={12} className="text-zinc-500" /></button>
            </div>
          ) : <span className="text-sm text-zinc-400">Drop a document or click to browse</span>}
        </div>
        <button onClick={handleClassify} disabled={!file || processing}
          className="px-5 py-2 rounded-lg font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 flex items-center gap-2 whitespace-nowrap">
          {processing ? <Loader2 size={16} className="animate-spin" /> : <Tag size={16} />}
          {processing ? 'Classifying...' : 'Classify'}
        </button>
      </div>

      {result?.error && (
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4">
          <span className="text-sm text-rose-400">{result.error}</span>
        </div>
      )}

      {result?.doc_type && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
          <CheckCircle size={48} className="mx-auto text-emerald-400 mb-4" />
          <p className="text-2xl font-bold capitalize mb-2">{result.doc_type.replace(/_/g, ' ')}</p>
          <div className="flex justify-center gap-4 text-sm text-zinc-400">
            <span>Confidence: <strong className="text-emerald-400">{(result.confidence * 100).toFixed(0)}%</strong></span>
            <span>Fields detected: <strong className="text-indigo-400">{result.fields_found}</strong></span>
          </div>
        </div>
      )}

      {!result && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <Tag size={40} className="mx-auto text-zinc-700 mb-3" />
          <p className="text-zinc-500 text-sm">Upload a document to automatically detect its type</p>
          <p className="text-zinc-600 text-xs mt-1">Supports: Invoice, Receipt, Contract, Medical, Form, ID Card, Bank Statement, and more</p>
        </div>
      )}
    </div>
  )
}
