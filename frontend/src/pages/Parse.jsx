import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Upload, FileText, Play, Loader2, X, Eye, Code, AlertTriangle, ChevronRight, ZoomIn, ZoomOut, Download, ChevronLeft, BookOpen, History, Clock, Type, Braces, List, RotateCcw, Copy, Check } from 'lucide-react'
import { api } from '../api'

const TIERS = [
  { id: 'agentic_plus', name: 'Agentic Plus', desc: 'Premium AI + charts + grounding' },
  { id: 'agentic', name: 'Agentic', desc: 'Full AI pipeline (default)' },
  { id: 'cost_effective', name: 'Cost Effective', desc: 'Balanced speed and quality' },
  { id: 'fast', name: 'Fast', desc: 'Rule-based, no AI' },
]

const SLA_TIERS = [
  { id: 'standard', name: 'Standard (85%)', desc: 'Best-effort, cheapest provider' },
  { id: 'premium', name: 'Premium (95%)', desc: 'High accuracy + corrections' },
  { id: 'guaranteed', name: 'Guaranteed (99%)', desc: 'Near-perfect + human review' },
]

function MarkdownRenderer({ markdown, fieldBboxes, onFieldHover, hoveredField, activeField }) {
  if (!markdown) return <p className="text-zinc-600 text-sm italic">No markdown output</p>

  const fieldNames = (fieldBboxes || []).map(b => b.field)

  function findFieldForLine(line) {
    const clean = line.replace(/[#*\-|`]/g, '').trim().toLowerCase()
    for (const f of fieldNames) {
      const label = f.replace(/_/g, ' ').toLowerCase()
      if (clean.includes(label) || label.includes(clean.slice(0, 20))) return f
    }
    return null
  }

  return (
    <div className="leading-relaxed">
      {markdown.split('\n').map((line, i) => {
        const field = findFieldForLine(line)
        const isHighlighted = field && (field === hoveredField || field === activeField)
        const hoverProps = field && onFieldHover ? {
          onMouseEnter: () => onFieldHover(field),
          onMouseLeave: () => onFieldHover(null),
          style: { cursor: 'pointer' },
        } : {}

        if (line.startsWith('### ')) return <h3 key={i} {...hoverProps} className={`text-[15px] font-semibold mt-5 mb-1 rounded px-1 -mx-1 transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-300' : 'text-zinc-100 hover:bg-zinc-800/50'}`}>{line.slice(4)}</h3>
        if (line.startsWith('## ')) return <h2 key={i} {...hoverProps} className={`text-[17px] font-bold mt-6 mb-1.5 rounded px-1 -mx-1 transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-300' : 'text-zinc-100 hover:bg-zinc-800/50'}`}>{line.slice(3)}</h2>
        if (line.startsWith('# ')) return <h1 key={i} {...hoverProps} className={`text-xl font-bold mt-6 mb-2 rounded px-1 -mx-1 transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-300' : 'text-zinc-100 hover:bg-zinc-800/50'}`}>{line.slice(2)}</h1>
        if (line === '---') return <hr key={i} className="border-zinc-700 my-4" />
        if (line.startsWith('| ') && line.includes(' | ')) {
          if (line.includes('---')) return null
          const cells = line.split('|').filter(c => c.trim())
          return (
            <div key={i} {...hoverProps} className={`flex gap-3 py-1.5 text-[13px] border-b border-zinc-800/30 rounded px-2 -mx-1 transition-all ${isHighlighted ? 'bg-indigo-500/20 border-indigo-500/30' : 'opacity-70 hover:opacity-100 hover:bg-zinc-800/40'}`}>
              <span className={`w-44 shrink-0 font-medium ${isHighlighted ? 'text-indigo-300' : 'text-zinc-500'}`}>{cells[0]?.trim()}</span>
              <span className={`font-mono text-xs ${isHighlighted ? 'text-white' : 'text-zinc-300'}`}>{cells.slice(1).map(c => c.trim()).join(' | ')}</span>
            </div>
          )
        }
        if (line.startsWith('- **')) {
          const inner = line.slice(2)
          return <p key={i} {...hoverProps} className={`text-[13px] pl-3 py-0.5 rounded transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-200' : 'text-zinc-400 opacity-80 hover:opacity-100 hover:bg-zinc-800/40'}`}>• {renderInline(inner)}</p>
        }
        if (line.startsWith('- ')) return <p key={i} {...hoverProps} className={`text-[13px] pl-3 py-0.5 rounded transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-200' : 'text-zinc-400 opacity-80 hover:opacity-100 hover:bg-zinc-800/40'}`}>• {line.slice(2)}</p>

        if (line.trim() === '') return <div key={i} className="h-2" />

        return <p key={i} {...hoverProps} className={`text-[13px] leading-relaxed rounded px-1 -mx-1 transition-colors ${isHighlighted ? 'bg-indigo-500/20 text-indigo-200' : 'text-zinc-400 opacity-80 hover:opacity-100 hover:bg-zinc-800/40'}`}>{renderInline(line)}</p>
      })}
    </div>
  )
}

function renderInline(text) {
  const parts = []
  let remaining = text
  let key = 0
  while (remaining.length > 0) {
    const boldStart = remaining.indexOf('**')
    if (boldStart === -1) { parts.push(<span key={key++}>{remaining}</span>); break }
    if (boldStart > 0) parts.push(<span key={key++}>{remaining.slice(0, boldStart)}</span>)
    const boldEnd = remaining.indexOf('**', boldStart + 2)
    if (boldEnd === -1) { parts.push(<span key={key++}>{remaining.slice(boldStart)}</span>); break }
    parts.push(<strong key={key++} className="font-semibold" style={{ color: 'var(--text-primary)' }}>{remaining.slice(boldStart + 2, boldEnd)}</strong>)
    remaining = remaining.slice(boldEnd + 2)
  }
  return parts
}

function DocumentViewer({ pages, fieldBboxes, activeField, hoveredField, onFieldClick, onFieldHover, zoom }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const target = activeField || hoveredField
    if (target && containerRef.current) {
      const el = containerRef.current.querySelector(`[data-bbox-field="${target}"]`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [activeField, hoveredField])

  if (!pages || pages.length === 0) return null

  return (
    <div ref={containerRef} className="flex flex-col items-center gap-4">
      {pages.map((page) => {
        const pageBboxes = fieldBboxes.filter(b => b.page === page.page)
        return (
          <div key={page.page} className="relative inline-block bg-white rounded shadow-lg" style={{ width: page.width * zoom, height: page.height * zoom }}>
            <img src={`data:image/png;base64,${page.image_base64}`} alt={`Page ${page.page}`}
              className="block rounded" style={{ width: page.width * zoom, height: page.height * zoom }} draggable={false} />
            <svg className="absolute top-0 left-0 pointer-events-none" width={page.width * zoom} height={page.height * zoom}
              viewBox={`0 0 ${page.width} ${page.height}`}>
              {pageBboxes.map((b, i) => {
                const isActive = activeField === b.field
                const isHovered = hoveredField === b.field
                const isHighlighted = isActive || isHovered
                const hasAny = activeField || hoveredField
                return (
                  <g key={i} data-bbox-field={b.field} style={{ opacity: isHighlighted ? 1 : (hasAny ? 0.1 : 0), transition: 'opacity 0.15s' }}>
                    <rect x={b.x} y={b.y} width={b.width} height={b.height}
                      fill={isHighlighted ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.05)'}
                      stroke={isHighlighted ? '#818cf8' : '#6366f1'}
                      strokeWidth={isHighlighted ? 2.5 : 1} rx={2}
                      className="pointer-events-auto cursor-pointer"
                      onClick={() => onFieldClick(b.field)}
                      onMouseEnter={() => onFieldHover(b.field)}
                      onMouseLeave={() => onFieldHover(null)} />
                    {isHighlighted && (
                      <g>
                        <rect x={b.x} y={Math.max(b.y - 17, 0)}
                          width={Math.max(b.field.replace(/_/g, ' ').length * 5.8 + 10, 40)} height={14}
                          fill="#312e81" rx={2} />
                        <text x={b.x + 5} y={Math.max(b.y - 6, 8)} fill="#c7d2fe" fontSize={9} fontFamily="system-ui" fontWeight="600">
                          {b.field.replace(/_/g, ' ')}
                        </text>
                      </g>
                    )}
                  </g>
                )
              })}
            </svg>
          </div>
        )
      })}
    </div>
  )
}

export default function Playground() {
  const [file, setFile] = useState(null)
  const [tier, setTier] = useState('agentic')
  const [accuracyTier, setAccuracyTier] = useState('standard')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [rightTab, setRightTab] = useState('markdown')
  const [dragOver, setDragOver] = useState(false)
  const [activeField, setActiveField] = useState(null)
  const [hoveredField, setHoveredField] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [currentPage, setCurrentPage] = useState(1)
  const [showHistory, setShowHistory] = useState(false)
  const [history, setHistory] = useState([])
  const [mainTab, setMainTab] = useState('results')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.listParses().then(data => { if (Array.isArray(data)) setHistory(data.filter(j => j.status === 'completed').slice(0, 20)) }).catch(() => {})
  }, [result])

  const handleDrop = useCallback((e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) setFile(f) }, [])

  const handleParse = async () => {
    if (!file) return
    setProcessing(true); setResult(null); setActiveField(null); setHoveredField(null); setMainTab('results')
    try {
      const data = await api.uploadAndParse(file, tier, accuracyTier)
      setResult(data)
      setRightTab('markdown')
    } catch (err) {
      setResult({ status: 'failed', error: err.message })
    } finally { setProcessing(false) }
  }

  const handleFieldClick = (field) => setActiveField(prev => prev === field ? null : field)

  const handleDownload = (format) => {
    if (!result) return
    const isJson = format === 'json'
    const content = isJson
      ? JSON.stringify({ extraction: result.extraction, doc_type: result.doc_type, quality_report: result.quality_report, citations: result.citations }, null, 2)
      : (result.markdown || '')
    const blob = new Blob([content], { type: isJson ? 'application/json' : 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${file?.name || 'result'}.${isJson ? 'json' : 'md'}`; a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    const text = rightTab === 'json'
      ? JSON.stringify({ extraction: result?.extraction, doc_type: result?.doc_type }, null, 2)
      : rightTab === 'text' ? (result?.source_text || '') : (result?.markdown || '')
    navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500)
  }

  const pages = result?.pages || []
  const fieldBboxes = result?.field_bboxes || []
  const totalPages = pages.length
  const extraction = result?.extraction || {}
  const qr = result?.quality_report || {}
  const gr = result?.grounding_report || {}

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1800px] mx-auto">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Parse</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Upload a document to extract structured data with visual grounding</p>
        </div>
        <button onClick={() => setShowHistory(!showHistory)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${showHistory ? 'bg-indigo-500/10 text-indigo-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}>
          <History size={13} /> History
        </button>
      </div>

      {showHistory && history.length > 0 && (
        <div className="mb-3 bg-zinc-900 border border-zinc-800 rounded-xl p-3">
          <div className="space-y-1 max-h-[180px] overflow-auto">
            {history.map(job => (
              <div key={job.job_id} className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-zinc-800/50 text-xs group">
                <a href={api.getJobFileUrl(job.job_id)} target="_blank" rel="noopener" onClick={e => e.stopPropagation()} className="text-zinc-500 hover:text-indigo-400"><FileText size={11} /></a>
                <span className="text-zinc-300 truncate flex-1 cursor-pointer"
                  onClick={() => { api.getParse(job.job_id).then(d => { if (d.extraction) { setResult({ status: 'completed', ...d }); setShowHistory(false); setMainTab('results') } }).catch(() => {}) }}>
                  {job.filename || job.job_id}
                </span>
                <span className="text-zinc-600 capitalize text-[10px]">{job.doc_type || ''}</span>
                <span className="text-zinc-600 text-[10px]">{job.created_at ? new Date(job.created_at).toLocaleDateString() : ''}</span>
                <button onClick={() => { api.rerunJob(job.job_id, tier).then(d => { if (d.extraction) { setResult({ status: 'completed', ...d }); setShowHistory(false) } }).catch(() => {}) }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-zinc-700 rounded text-zinc-500 hover:text-emerald-400" title="Rerun">
                  <RotateCcw size={10} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload bar */}
      <div className="flex gap-3 mb-4">
        <div className={`flex-1 border-2 border-dashed rounded-xl p-3 text-center transition-colors cursor-pointer ${dragOver ? 'border-indigo-500 bg-indigo-500/5' : file ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-zinc-700 hover:border-zinc-600'}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput').click()}>
          <input id="fileInput" type="file" className="hidden" onChange={e => setFile(e.target.files[0])}
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp,.heic,.heif,.avif,.svg,.gif,.docx,.xlsx,.xls,.csv,.tsv,.html,.htm,.txt,.json,.xml,.yaml,.yml" />
          {file ? (
            <div className="flex items-center justify-center gap-2">
              <FileText size={16} className="text-emerald-400" />
              <span className="text-sm font-medium">{file.name}</span>
              <span className="text-xs text-zinc-500">{(file.size / 1024).toFixed(1)} KB</span>
              <button onClick={e => { e.stopPropagation(); setFile(null); setResult(null) }} className="ml-1 p-0.5 hover:bg-zinc-800 rounded"><X size={11} className="text-zinc-500" /></button>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <Upload size={16} className="text-zinc-600" />
              <span className="text-sm text-zinc-400">Drop a document here or click to browse</span>
            </div>
          )}
        </div>
        <select value={tier} onChange={e => setTier(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500 self-center">
          {TIERS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select value={accuracyTier} onChange={e => setAccuracyTier(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500 self-center"
          title="Accuracy SLA tier">
          {SLA_TIERS.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <button onClick={handleParse} disabled={!file || processing}
          className="px-5 py-2 rounded-lg font-medium text-sm flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 whitespace-nowrap self-center">
          {processing ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {processing ? 'Processing...' : 'Parse'}
        </button>
      </div>

      {/* Error */}
      {result?.status === 'failed' && (
        <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 mb-4">
          <div className="flex items-center gap-2"><AlertTriangle size={14} className="text-rose-400" /><span className="text-sm font-medium text-rose-400">Failed</span></div>
          <p className="text-xs text-zinc-400 mt-1">{result.error}</p>
        </div>
      )}

      {/* Build / Results / Code — top tab bar */}
      {result?.status === 'completed' && (
        <>
          <div className="flex items-center border-b border-zinc-800 mb-0">
            {[
              { key: 'results', label: 'Results' },
              { key: 'code', label: '</> Code' },
            ].map(t => (
              <button key={t.key} onClick={() => setMainTab(t.key)}
                className={`px-5 py-2 text-sm font-medium transition-colors ${mainTab === t.key ? 'text-white border-b-2 border-indigo-500' : 'text-zinc-500 hover:text-zinc-300'}`}>
                {t.label}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-3 px-3 text-[10px]">
              {result.sla && (
                <span className={`px-2 py-0.5 rounded-full font-semibold ${result.sla.met_sla ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                  SLA {result.sla.met_sla ? 'MET' : 'MISSED'} ({(result.sla.achieved_accuracy * 100).toFixed(0)}%/{(result.sla.accuracy_target * 100).toFixed(0)}%)
                </span>
              )}
              {result.routing && (
                <span className="text-zinc-500" title={`Reason: ${result.routing.reason}`}>
                  via {result.routing.provider}
                </span>
              )}
              {result.processing_time_ms && <span className="text-zinc-500">{result.processing_time_ms}ms</span>}
              {result.job_id && (
                <a href={api.exportAudit(result.job_id, 'json')} download className="text-indigo-400 hover:text-indigo-300 cursor-pointer" title="Download compliance audit">
                  <Download size={12} />
                </a>
              )}
              <span className="text-emerald-400 font-semibold flex items-center gap-1"><Check size={10} /> SUCCESS</span>
            </div>
          </div>

          {/* ===== RESULTS TAB — SIDE BY SIDE LAYOUT ===== */}
          {mainTab === 'results' && (
            <div className="flex flex-col lg:flex-row gap-0 border border-zinc-800 rounded-b-xl overflow-hidden" style={{ height: 'calc(100vh - 280px)', minHeight: 500 }}>
              {/* LEFT PANEL — Document Viewer */}
              <div className="lg:w-1/2 flex flex-col border-r border-zinc-800 bg-zinc-950">
                {/* Doc toolbar */}
                <div className="flex items-center gap-1 px-3 py-2 border-b border-zinc-800 bg-zinc-900 shrink-0">
                  <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage <= 1}
                    className="p-1 hover:bg-zinc-800 rounded text-zinc-400 disabled:opacity-30"><ChevronLeft size={14} /></button>
                  <span className="text-[11px] text-zinc-400 min-w-[55px] text-center font-medium">{currentPage} of {totalPages || 1}</span>
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage >= totalPages}
                    className="p-1 hover:bg-zinc-800 rounded text-zinc-400 disabled:opacity-30"><ChevronRight size={14} /></button>
                  <span className="mx-2 w-px h-4 bg-zinc-700" />
                  <button onClick={() => setZoom(z => Math.max(0.3, z - 0.15))} className="p-1 hover:bg-zinc-800 rounded text-zinc-400"><ZoomOut size={13} /></button>
                  <span className="text-[10px] text-zinc-500 w-10 text-center">{Math.round(zoom * 100)}%</span>
                  <button onClick={() => setZoom(z => Math.min(3, z + 0.15))} className="p-1 hover:bg-zinc-800 rounded text-zinc-400"><ZoomIn size={13} /></button>
                  <button onClick={() => setZoom(1)} className="text-[9px] text-zinc-500 hover:text-zinc-300 ml-1">Reset</button>
                  <div className="ml-auto flex gap-1">
                    <button onClick={() => handleDownload('json')} className="p-1 hover:bg-zinc-800 rounded text-zinc-500" title="Download JSON"><Download size={12} /></button>
                    <button onClick={() => handleDownload('markdown')} className="p-1 hover:bg-zinc-800 rounded text-zinc-500" title="Download Markdown"><BookOpen size={12} /></button>
                  </div>
                </div>
                {/* Doc content */}
                <div className="flex-1 overflow-auto p-4 flex justify-center">
                  {pages.length > 0 ? (
                    <DocumentViewer
                      pages={pages.filter(p => p.page === currentPage)}
                      fieldBboxes={fieldBboxes.filter(b => b.page === currentPage)}
                      activeField={activeField} hoveredField={hoveredField}
                      onFieldClick={handleFieldClick} onFieldHover={setHoveredField} zoom={zoom} />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-zinc-600 gap-2">
                      <Eye size={32} />
                      <p className="text-xs">No document preview available</p>
                    </div>
                  )}
                </div>
              </div>

              {/* RIGHT PANEL — Markdown / Text / JSON / Items */}
              <div className="lg:w-1/2 flex flex-col bg-zinc-900" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                {/* Right tab bar */}
                <div className="flex items-center border-b border-zinc-800 shrink-0">
                  {[
                    { key: 'markdown', icon: BookOpen, label: 'Markdown' },
                    { key: 'text', icon: Type, label: 'T' },
                    { key: 'json', icon: Braces, label: '{}' },
                    { key: 'items', icon: List, label: 'Items' },
                  ].map(t => (
                    <button key={t.key} onClick={() => setRightTab(t.key)}
                      className={`px-3 py-2 text-xs font-medium transition-colors flex items-center gap-1.5 ${
                        rightTab === t.key ? 'text-indigo-400 border-b-2 border-indigo-400 bg-zinc-800/30' : 'text-zinc-500 hover:text-zinc-300'
                      }`}>
                      <t.icon size={12} />{t.label}
                    </button>
                  ))}
                  <div className="ml-auto flex items-center gap-1 px-2">
                    <button onClick={handleCopy} className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-300" title="Copy">
                      {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
                {/* Right content */}
                <div className="flex-1 overflow-auto p-5">
                  {rightTab === 'markdown' && <MarkdownRenderer markdown={result.markdown} fieldBboxes={fieldBboxes} onFieldHover={setHoveredField} hoveredField={hoveredField} activeField={activeField} />}

                  {rightTab === 'text' && (
                    <pre className="text-[13px] font-mono whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {result.source_text || result.text || 'No raw text available'}
                    </pre>
                  )}

                  {rightTab === 'json' && (
                    <pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                      {JSON.stringify({
                        job_id: result.job_id, doc_type: result.doc_type,
                        extraction, quality_report: qr, grounding_report: gr,
                        citations: result.citations, field_confidences: result.field_confidences,
                      }, null, 2)}
                    </pre>
                  )}

                  {rightTab === 'items' && (
                    <div className="space-y-2">
                      {(result.items || []).length === 0 && <p className="text-zinc-500 text-sm italic">No structured items available</p>}
                      {(result.items || []).map((item, i) => (
                        <div key={i} className="flex gap-3 p-2 rounded-lg hover:bg-indigo-500/10 transition-colors cursor-pointer"
                          onMouseEnter={() => item.bbox && setHoveredField(item.field || null)}
                          onMouseLeave={() => setHoveredField(null)}>
                          <span className={`shrink-0 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                            item.type === 'heading' ? 'bg-violet-500/15 text-violet-400' :
                            item.type === 'image' ? 'bg-amber-500/15 text-amber-400' :
                            item.type === 'table' ? 'bg-sky-500/15 text-sky-400' :
                            'bg-zinc-700/30 text-zinc-400'
                          }`}>{item.type}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-[13px] leading-snug" style={{ color: 'var(--text-primary)' }}>{String(item.value || item.md || '').slice(0, 200)}</p>
                            {item.bbox && (
                              <p className="text-[9px] text-zinc-600 mt-0.5 font-mono">
                                bbox: {typeof item.bbox.x === 'number' ? `${item.bbox.x.toFixed(0)},${item.bbox.y.toFixed(0)} ${item.bbox.w?.toFixed(0)}×${item.bbox.h?.toFixed(0)}` : JSON.stringify(item.bbox)}
                                {item.bbox.confidence != null && ` conf:${(item.bbox.confidence * 100).toFixed(0)}%`}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Stats footer */}
                <div className="flex flex-wrap gap-2 px-4 py-2 border-t shrink-0" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-secondary)' }}>
                  {[
                    { label: 'Type', value: result.doc_type, color: 'text-sky-400' },
                    { label: 'Fields', value: Object.keys(extraction).filter(k => !k.startsWith('_')).length, color: 'text-amber-400' },
                    { label: 'Quality', value: `${Math.round((qr.overall_score || 0) * 100)}%`, color: 'text-indigo-400' },
                    { label: 'Grounding', value: `${Math.round((gr.grounding_rate || 0) * 100)}%`, color: 'text-emerald-400' },
                    ...(result.processing_time_ms ? [{ label: 'Time', value: `${result.processing_time_ms}ms`, color: 'text-purple-400' }] : []),
                  ].map(s => (
                    <span key={s.label} className="text-[10px] text-zinc-500">
                      {s.label}: <span className={`font-semibold capitalize ${s.color}`}>{s.value}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ===== CODE TAB ===== */}
          {mainTab === 'code' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
              {[
                { lang: 'Python', code: `from pathlib import Path\nfrom pixora import PixoraClient\n\nclient = PixoraClient(api_key="your-api-key")\n\nresult = client.parse(\n    file="./document.pdf",\n    tier="${tier}",\n    expand=["markdown", "text", "items"],\n)\n\nprint(f"Type: {result.doc_type}")\nprint(f"Fields: {len(result.extraction)}")\n\n# Save outputs\nPath("output.md").write_text(result.markdown or "")\nPath("output.txt").write_text(result.text or "")\n\n# Structured items with bounding boxes\nfor item in result.items:\n    print(f"  [{item['type']}] {item['value'][:50]}")\n\n# Per-field citations\nfor cite in result.citations:\n    print(f"  {cite['field']}: page {cite['page']}, "\n          f"conf {cite['overall_confidence']}")` },
                { lang: 'JavaScript', code: `import { PixoraClient } from "@pixora/sdk";\nimport fs from "fs";\n\nconst client = new PixoraClient({ apiKey: "your-api-key" });\n\nasync function main() {\n  const result = await client.parse({\n    file: fs.createReadStream("./document.pdf"),\n    tier: "${tier}",\n    expand: ["markdown", "text", "items"],\n  });\n\n  console.log(\`Type: \${result.doc_type}\`);\n  console.log(\`Fields: \${Object.keys(result.extraction).length}\`);\n\n  fs.writeFileSync("output.md", result.markdown ?? "");\n  fs.writeFileSync("output.txt", result.text ?? "");\n\n  for (const item of result.items) {\n    console.log(\`  [\${item.type}] \${item.value?.slice(0, 50)}\`);\n  }\n}\n\nmain().catch(console.error);` },
              ].map(({ lang, code }) => (
                <div key={lang} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 border-b border-zinc-800">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400">{lang}</span>
                  </div>
                  <pre className="p-4 text-xs text-zinc-300 font-mono whitespace-pre-wrap overflow-auto max-h-[500px]">{code}</pre>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!result && !processing && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-16 text-center">
          <Eye size={36} className="mx-auto text-zinc-700 mb-3" />
          <p className="text-zinc-500 text-sm">Upload a document to see visual field extraction</p>
          <p className="text-zinc-600 text-xs mt-1">PDF, images, DOCX, CSV, and more</p>
        </div>
      )}
    </div>
  )
}
