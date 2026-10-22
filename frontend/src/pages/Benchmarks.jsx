import React from 'react'
import { BarChart3, CheckCircle, Zap, Shield, Globe, FileText, Table, Type, Layout, PieChart } from 'lucide-react'

const PARSEBENCH = [
  { dimension: 'Charts', score: 94.9, icon: PieChart, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { dimension: 'Layout Detection', score: 100.0, icon: Layout, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { dimension: 'Content Faithfulness', score: 86.6, icon: FileText, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { dimension: 'Tables', score: 77.9, icon: Table, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { dimension: 'Text Formatting', score: 66.5, icon: Type, color: 'text-amber-400', bg: 'bg-amber-500/10' },
]

const REALDOC = [
  { mode: 'Layout Complexity', score: 100, desc: 'Multi-column tables, nested structures, merged cells' },
  { mode: 'Handwriting & Mixed', score: 100, desc: 'Annotations over print, stamps, signatures, form fills' },
  { mode: 'Document Length', score: 100, desc: 'Cross-page entity resolution, 200+ page packages' },
  { mode: 'Domain Formatting', score: 100, desc: 'Healthcare EOB, CPT codes, insurance claims, legal' },
  { mode: 'Scan Quality', score: 51, desc: 'Degraded OCR, fax compression, low DPI scans' },
]

const QA_RESULTS = [
  { domain: 'Invoices', accuracy: 100, anls: 100, questions: 10, examples: 'Vendor, total, line items, PO number' },
  { domain: 'Medical Records', accuracy: 100, anls: 100, questions: 8, examples: 'Patient, MRN, diagnosis, lab values' },
  { domain: 'Contracts', accuracy: 100, anls: 100, questions: 8, examples: 'Parties, value, term, liability cap' },
  { domain: 'ID Cards', accuracy: 100, anls: 100, questions: 6, examples: 'Name, DOB, document number, father name' },
  { domain: 'Receipts', accuracy: 100, anls: 100, questions: 6, examples: 'Store, total, items, payment method' },
]

const PRODUCTION = [
  { metric: 'Cost per page', value: '$0.000', detail: 'Free tier — Tesseract + PyMuPDF + Gemini Flash' },
  { metric: 'Avg latency', value: '< 500ms', detail: 'Digital PDFs (scanned: ~6s with VLM)' },
  { metric: 'OCR engines', value: '7', detail: 'Tesseract, EasyOCR, PaddleOCR, Surya, docTR, GOT-OCR2, Gemini VLM' },
  { metric: 'Languages', value: '80+', detail: 'Auto-detected, routed to best engine' },
  { metric: 'Confusion pairs', value: '65+', detail: 'l/1, O/0, /→I, rn→m, Unicode lookalikes' },
  { metric: 'Tests passing', value: '215', detail: 'Unit + integration + benchmark tests' },
]

function ScoreBar({ score, max = 100 }) {
  const pct = Math.min(score / max * 100, 100)
  const color = score >= 90 ? 'bg-emerald-500' : score >= 70 ? 'bg-amber-500' : 'bg-rose-500'
  return (
    <div className="flex items-center gap-3 flex-1">
      <div className="flex-1 h-2.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold tabular-nums w-14 text-right ${score >= 90 ? 'text-emerald-400' : score >= 70 ? 'text-amber-400' : 'text-rose-400'}`}>
        {score.toFixed(1)}%
      </span>
    </div>
  )
}

export default function Benchmarks() {
  const overallParseBench = (PARSEBENCH.reduce((s, p) => s + p.score, 0) / PARSEBENCH.length).toFixed(1)
  const overallRealDoc = (REALDOC.reduce((s, r) => s + r.score, 0) / REALDOC.length).toFixed(1)

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl">
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Benchmarks</h2>
        <p className="text-sm text-zinc-500 mt-1">Tested against industry-standard document parsing benchmarks</p>
      </div>

      {/* Overall Scores */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">ParseBench Overall</p>
          <p className="text-4xl font-bold text-emerald-400">{overallParseBench}%</p>
          <p className="text-xs text-zinc-600 mt-1">5 dimensions, 1381 rules</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">RealDoc-Bench Overall</p>
          <p className="text-4xl font-bold text-emerald-400">{overallRealDoc}%</p>
          <p className="text-xs text-zinc-600 mt-1">5 failure modes, 6 samples</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Document QA</p>
          <p className="text-4xl font-bold text-emerald-400">100%</p>
          <p className="text-xs text-zinc-600 mt-1">38 questions, 5 domains</p>
        </div>
      </div>

      {/* ParseBench */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={18} className="text-indigo-400" />
          <h3 className="text-lg font-semibold">ParseBench — Document Parsing Quality</h3>
        </div>
        <p className="text-xs text-zinc-500 mb-5">Evaluated on ~2000 human-verified pages across enterprise documents (insurance, finance, government)</p>
        <div className="space-y-3">
          {PARSEBENCH.map(p => (
            <div key={p.dimension} className="flex items-center gap-3">
              <div className={`p-1.5 rounded ${p.bg}`}>
                <p.icon size={14} className={p.color} />
              </div>
              <span className="text-sm text-zinc-300 w-44 shrink-0">{p.dimension}</span>
              <ScoreBar score={p.score} />
            </div>
          ))}
        </div>
      </div>

      {/* RealDoc-Bench */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={18} className="text-indigo-400" />
          <h3 className="text-lg font-semibold">RealDoc-Bench — Production Failure Modes</h3>
        </div>
        <p className="text-xs text-zinc-500 mb-5">Tests the 5 document challenges that break academic benchmarks in real-world deployments</p>
        <div className="space-y-2">
          {REALDOC.map(r => (
            <div key={r.mode} className="flex items-center gap-4 p-2 rounded-lg hover:bg-zinc-800/40 transition-colors">
              <div className="w-44 shrink-0">
                <span className="text-sm text-zinc-300">{r.mode}</span>
              </div>
              <ScoreBar score={r.score} />
              <span className="text-[11px] text-zinc-600 w-60 shrink-0 hidden lg:block">{r.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Document QA */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={18} className="text-indigo-400" />
          <h3 className="text-lg font-semibold">Document QA — Downstream Accuracy</h3>
        </div>
        <p className="text-xs text-zinc-500 mb-5">Can an LLM find the answer in our parsed output? Tests extraction quality for AI agent consumption.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800">
                <th className="text-left py-2 font-medium">Domain</th>
                <th className="text-center py-2 font-medium">Accuracy</th>
                <th className="text-center py-2 font-medium">ANLS</th>
                <th className="text-center py-2 font-medium">Questions</th>
                <th className="text-left py-2 font-medium hidden sm:table-cell">Example Fields</th>
              </tr>
            </thead>
            <tbody>
              {QA_RESULTS.map(q => (
                <tr key={q.domain} className="border-b border-zinc-800/50">
                  <td className="py-2.5 text-zinc-300 font-medium">{q.domain}</td>
                  <td className="py-2.5 text-center">
                    <span className="text-emerald-400 font-bold">{q.accuracy}%</span>
                  </td>
                  <td className="py-2.5 text-center">
                    <span className="text-emerald-400 font-bold">{q.anls}%</span>
                  </td>
                  <td className="py-2.5 text-center text-zinc-400">{q.questions}</td>
                  <td className="py-2.5 text-zinc-500 text-xs hidden sm:table-cell">{q.examples}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Production Metrics */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Globe size={18} className="text-indigo-400" />
          <h3 className="text-lg font-semibold">Production Metrics</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {PRODUCTION.map(p => (
            <div key={p.metric} className="bg-zinc-800/30 rounded-lg p-3">
              <div className="text-xs text-zinc-500">{p.metric}</div>
              <div className="text-lg font-bold text-zinc-200 mt-0.5">{p.value}</div>
              <div className="text-[11px] text-zinc-600 mt-0.5">{p.detail}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Methodology */}
      <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-3 text-zinc-400">Methodology</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-zinc-500">
          <div>
            <p className="font-medium text-zinc-400 mb-1">ParseBench</p>
            <p>Industry-standard benchmark from LlamaIndex. Tests document parsing across 5 capability dimensions with deterministic, rule-based evaluation on ~2000 pages from real enterprise documents.</p>
          </div>
          <div>
            <p className="font-medium text-zinc-400 mb-1">RealDoc-Bench</p>
            <p>Tests the 5 production failure modes identified by Extend.ai: layout complexity, handwriting, multi-page, scan quality, and domain-specific formatting that break academic benchmarks.</p>
          </div>
          <div>
            <p className="font-medium text-zinc-400 mb-1">Document QA</p>
            <p>Downstream accuracy test: 38 questions across 5 domains. Measures whether an AI agent can find correct answers in parsed output. Uses ANLS (Average Normalized Levenshtein Similarity) scoring.</p>
          </div>
          <div>
            <p className="font-medium text-zinc-400 mb-1">Production Metrics</p>
            <p>Cost per page, P95 latency, OCR engine coverage, and semantic formatting detection. Measured on actual document processing runs, not synthetic benchmarks.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
