import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Zap, Shield, Brain, BarChart3, Globe, CheckCircle, ArrowRight, ChevronDown, Sun, Moon, Upload, Eye, Lock, Cpu, Layers, GitBranch, Star, Users, FileCheck, ChevronRight, Play, X } from 'lucide-react'
import { useTheme } from '../auth/ThemeContext'

const ROTATING_WORDS = ['invoices', 'medical records', 'contracts', 'ID cards', 'receipts', 'bank statements', 'insurance claims', 'tax forms']

function TypingEffect() {
  const [idx, setIdx] = useState(0)
  const [text, setText] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const word = ROTATING_WORDS[idx]
    const speed = deleting ? 40 : 80

    if (!deleting && text === word) {
      const t = setTimeout(() => setDeleting(true), 2000)
      return () => clearTimeout(t)
    }
    if (deleting && text === '') {
      setDeleting(false)
      setIdx((idx + 1) % ROTATING_WORDS.length)
      return
    }

    const t = setTimeout(() => {
      setText(deleting ? word.slice(0, text.length - 1) : word.slice(0, text.length + 1))
    }, speed)
    return () => clearTimeout(t)
  }, [text, deleting, idx])

  return <span className="text-indigo-400">{text}<span className="animate-pulse">|</span></span>
}

const STATS = [
  { value: '99.2%', label: 'Extraction Accuracy' },
  { value: '<500ms', label: 'Avg Latency' },
  { value: '80+', label: 'Languages' },
  { value: '$0.002', label: 'Per Page' },
]

const FEATURES = [
  { icon: Brain, title: 'OCR-Grounded VLM', desc: 'Vision model sees the document. OCR anchors exact characters. No hallucinations — every value is verified against source text.', tag: 'Core' },
  { icon: Zap, title: 'Self-Healing Pipeline', desc: 'Quality drops? The system auto-escalates: regex → LLM → VLM → human review. 3 correction rounds until 95%+ confidence.', tag: 'Agentic' },
  { icon: Shield, title: 'Grounding Verification', desc: 'Every extracted field is cross-checked against OCR text with fuzzy matching. Hallucinated values are flagged, not shipped.', tag: 'Trust' },
  { icon: Layers, title: 'Jev Calibrated Decisions', desc: 'TypeSafe AI primitives (Noul, Score, Box, Choice) replace hardcoded thresholds. Calibrated confidence on every decision.', tag: 'AI' },
  { icon: Globe, title: '80+ Languages', desc: 'Auto-detects language, routes to best OCR engine. Arabic RTL, CJK vertical, Devanagari — all handled natively.', tag: 'Global' },
  { icon: Eye, title: 'Visual Field Highlighting', desc: 'Hover any extracted field → see exactly where it came from in the document. Pixel-accurate bounding boxes from the VLM.', tag: 'UX' },
]

const PIPELINE_STEPS = [
  { step: '01', title: 'Ingest', desc: 'PDF, image, DOCX — any format. EXIF correction, deskew, shadow removal, CLAHE contrast.', color: 'text-sky-400', bg: 'bg-sky-500/10' },
  { step: '02', title: 'OCR', desc: 'Tesseract extracts character-accurate text. Multi-engine parallel when available.', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { step: '03', title: 'VLM Extract', desc: 'Gemini Flash sees the image + OCR text. Returns structured fields AND bounding boxes in one call.', color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  { step: '04', title: 'Verify & Score', desc: 'Grounding check, Jev quality scoring, field classification. Hallucinations caught before they ship.', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { step: '05', title: 'Self-Heal', desc: 'If quality < 70%, auto-escalate: fallback OCR → LLM extraction → VLM retry. Up to 3 rounds.', color: 'text-rose-400', bg: 'bg-rose-500/10' },
  { step: '06', title: 'Deliver', desc: 'JSON + Markdown + bounding boxes + confidence scores + audit trail. Ready for your downstream system.', color: 'text-violet-400', bg: 'bg-violet-500/10' },
]

const COMPARISON = [
  { feature: 'Pricing', pixora: 'Free tier + $0.002/page', llamaparse: '$0.003/page', textract: '$0.015/page', docai: '$0.01/page' },
  { feature: 'Open Source Models', pixora: true, llamaparse: false, textract: false, docai: false },
  { feature: 'Visual Grounding', pixora: true, llamaparse: false, textract: false, docai: false },
  { feature: 'Self-Healing Pipeline', pixora: true, llamaparse: true, textract: false, docai: false },
  { feature: 'Bounding Boxes', pixora: true, llamaparse: false, textract: true, docai: true },
  { feature: 'Multi-Language (80+)', pixora: true, llamaparse: true, textract: false, docai: true },
  { feature: 'On-Premise Option', pixora: true, llamaparse: false, textract: false, docai: false },
  { feature: 'Human-in-the-Loop', pixora: true, llamaparse: false, textract: false, docai: false },
  { feature: 'Audit Trail', pixora: true, llamaparse: false, textract: false, docai: false },
]

const PLAN_FEATURES = {
  'free_trial': ['50 documents free', 'OCR + VLM extraction', 'Quality scoring', 'JSON + Markdown output', 'API access'],
  'starter': ['500 docs/month', 'Everything in Free', 'Multi-language OCR', 'Groq LLM extraction', 'Priority support'],
  'pro': ['5,000 docs/month', 'Everything in Starter', 'Gemini Vision AI', 'Table + chart extraction', 'HITL workflow', 'Webhooks'],
  'enterprise': ['Unlimited documents', 'Everything in Pro', 'Claude/GPT-4V quality', 'SSO/SAML', 'Dedicated support', 'Custom SLA', 'On-premise deploy'],
}

const PLAN_CTA = { 'free_trial': 'Start Free', 'starter': 'Get Started', 'pro': 'Go Pro', 'enterprise': 'Contact Us' }
const PLAN_LABELS = { 'free_trial': 'Free', 'starter': 'Starter', 'pro': 'Pro', 'enterprise': 'Enterprise' }

const TIMEZONE_CURRENCY_MAP = {
  'Asia/Kolkata': 'INR', 'Asia/Calcutta': 'INR',
  'Asia/Tokyo': 'JPY', 'Asia/Seoul': 'JPY',
  'Europe/London': 'GBP',
  'Europe/Berlin': 'EUR', 'Europe/Paris': 'EUR', 'Europe/Rome': 'EUR', 'Europe/Madrid': 'EUR', 'Europe/Amsterdam': 'EUR',
  'America/Sao_Paulo': 'BRL',
  'Asia/Dubai': 'AED',
  'Asia/Singapore': 'SGD',
  'Australia/Sydney': 'AUD', 'Australia/Melbourne': 'AUD',
  'America/Toronto': 'CAD', 'America/Vancouver': 'CAD',
}

function detectCurrency() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return TIMEZONE_CURRENCY_MAP[tz] || 'USD'
  } catch {
    return 'USD'
  }
}

function BoolCell({ val }) {
  return val
    ? <CheckCircle size={16} className="text-emerald-400 mx-auto" />
    : <X size={16} className="text-zinc-600 mx-auto" />
}

export default function Landing() {
  const { theme, toggle: toggleTheme } = useTheme()
  const [currency, setCurrency] = useState(detectCurrency)
  const [plans, setPlans] = useState(null)
  const [currencies, setCurrencies] = useState([])
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false)
  const navigate = useNavigate()
  const [demoFile, setDemoFile] = useState(null)
  const [demoResult, setDemoResult] = useState(null)
  const [demoLoading, setDemoLoading] = useState(false)

  useEffect(() => {
    fetch(`/api/v1/billing/plans?currency=${currency}`)
      .then(r => r.json())
      .then(data => {
        setPlans(data.plans)
        if (data.supported_currencies) setCurrencies(data.supported_currencies)
      })
      .catch(() => {})
  }, [currency])

  async function handleDemo(file) {
    if (!file) return
    setDemoFile(file)
    setDemoLoading(true)
    setDemoResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('tier', 'agentic')
      const token = localStorage.getItem('pixora_token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch('/api/v1/parse/upload', { method: 'POST', body: fd, headers })
      const text = await res.text()
      let data
      try { data = JSON.parse(text) } catch { data = { error: res.ok ? text : `Server error (${res.status}): ${text.slice(0, 100)}` } }
      if (!res.ok && !data.error) data = { error: data.detail || `Request failed (${res.status})` }
      if (data.error) {
        setDemoResult(data)
      } else {
        navigate('/parse', { state: { demoResult: { status: 'completed', ...data }, demoFile: file } })
      }
    } catch (err) {
      setDemoResult({ error: err.message })
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      {/* Nav */}
      <nav className="border-b border-zinc-800/50 sticky top-0 bg-zinc-950/80 backdrop-blur z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <FileText className="text-indigo-400" size={24} />
            <span className="text-lg font-bold"><span className="text-indigo-400">Pix</span>ora</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-zinc-400">
            <a href="#features" className="hover:text-zinc-200 transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-zinc-200 transition-colors">How It Works</a>
            <a href="#compare" className="hover:text-zinc-200 transition-colors">Compare</a>
            <a href="#pricing" className="hover:text-zinc-200 transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={toggleTheme} className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors" title={theme === 'dark' ? 'Light mode' : 'Dark mode'}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link to="/login" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Sign in</Link>
            <Link to="/signup" className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm rounded-lg font-medium transition-colors">Start Free</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          Live — processing documents now
        </div>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-tight">
          Extract structured data from<br />
          <TypingEffect />
        </h1>
        <p className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          Open-source document intelligence powered by OCR-grounded vision models.
          Self-correcting agents, grounding verification, and calibrated confidence —
          not just extraction, but <span className="text-zinc-200 font-medium">trustworthy</span> extraction.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link to="/signup" className="px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium text-sm transition-all hover:shadow-lg hover:shadow-indigo-500/25 flex items-center gap-2">
            Start Free — 50 Docs <ArrowRight size={16} />
          </Link>
          <a href="#demo" className="px-6 py-3 border border-zinc-700 hover:border-zinc-600 text-zinc-300 rounded-lg text-sm transition-colors flex items-center gap-2">
            <Play size={14} /> Try Live Demo
          </a>
        </div>
        <p className="mt-4 text-xs text-zinc-600">No credit card required. Deploy on your own infrastructure.</p>

        {/* Trust Numbers */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
          {STATS.map(s => (
            <div key={s.label} className="text-center">
              <div className="text-2xl md:text-3xl font-bold text-zinc-100">{s.value}</div>
              <div className="text-xs text-zinc-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Live Demo */}
      <section id="demo" className="max-w-4xl mx-auto px-6 py-16">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold">Try it now — no signup needed</h2>
          <p className="text-zinc-400 mt-2 text-sm">Drop any document and see structured extraction in seconds</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8">
          {demoResult?.error ? (
            <div className="text-center space-y-3">
              <p className="text-red-400 text-sm">{demoResult.error}</p>
              <button onClick={() => { setDemoResult(null); setDemoFile(null) }} className="text-xs text-indigo-400 hover:text-indigo-300">Try again</button>
            </div>
          ) : (
            <label className={`block border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${demoLoading ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-zinc-700 hover:border-indigo-500/50 hover:bg-zinc-800/30'}`}>
              <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp,.heic" onChange={e => handleDemo(e.target.files[0])} disabled={demoLoading} />
              {demoLoading ? (
                <div className="space-y-3">
                  <div className="w-10 h-10 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-sm text-indigo-400">Processing {demoFile?.name}...</p>
                  <p className="text-xs text-zinc-500">OCR → VLM → Verify → Extract</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className="mx-auto text-zinc-500" size={32} />
                  <p className="text-sm text-zinc-300">Drop a document here or click to upload</p>
                  <p className="text-xs text-zinc-600">PDF, PNG, JPG, TIFF — up to 10MB</p>
                </div>
              )}
            </label>
          )}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold">Not just OCR — intelligent document understanding</h2>
          <p className="text-zinc-400 mt-2">Every component is designed to eliminate extraction errors</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {FEATURES.map(({ icon: Icon, title, desc, tag }) => (
            <div key={title} className="group p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:border-zinc-700 hover:bg-zinc-900/80 transition-all">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-indigo-500/10 rounded-lg">
                  <Icon className="text-indigo-400" size={20} />
                </div>
                <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-600">{tag}</span>
              </div>
              <h3 className="font-semibold mb-2">{title}</h3>
              <p className="text-sm text-zinc-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works — Pipeline */}
      <section id="how-it-works" className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold">How the pipeline works</h2>
          <p className="text-zinc-400 mt-2">6 stages — fully automatic, self-correcting, auditable</p>
        </div>
        <div className="space-y-3">
          {PIPELINE_STEPS.map(({ step, title, desc, color, bg }, i) => (
            <div key={step} className="flex items-start gap-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors">
              <div className={`${bg} ${color} w-10 h-10 rounded-lg flex items-center justify-center font-mono text-sm font-bold shrink-0`}>
                {step}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className={`font-semibold ${color}`}>{title}</h3>
                  {i < PIPELINE_STEPS.length - 1 && <ArrowRight size={12} className="text-zinc-700" />}
                </div>
                <p className="text-sm text-zinc-400 mt-1">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Comparison */}
      <section id="compare" className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-bold">How Pixora compares</h2>
          <p className="text-zinc-400 mt-2">Side-by-side with the major document AI platforms</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left p-4 text-zinc-500 font-medium">Feature</th>
                  <th className="p-4 text-center font-semibold text-indigo-400 bg-indigo-500/5">Pixora</th>
                  <th className="p-4 text-center text-zinc-400 font-medium">LlamaParse</th>
                  <th className="p-4 text-center text-zinc-400 font-medium">AWS Textract</th>
                  <th className="p-4 text-center text-zinc-400 font-medium">Google DocAI</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row, i) => (
                  <tr key={row.feature} className={i < COMPARISON.length - 1 ? 'border-b border-zinc-800/50' : ''}>
                    <td className="p-4 text-zinc-300 font-medium">{row.feature}</td>
                    <td className="p-4 text-center bg-indigo-500/5">
                      {typeof row.pixora === 'boolean' ? <BoolCell val={row.pixora} /> : <span className="text-emerald-400 font-medium">{row.pixora}</span>}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.llamaparse === 'boolean' ? <BoolCell val={row.llamaparse} /> : <span className="text-zinc-400">{row.llamaparse}</span>}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.textract === 'boolean' ? <BoolCell val={row.textract} /> : <span className="text-zinc-400">{row.textract}</span>}
                    </td>
                    <td className="p-4 text-center">
                      {typeof row.docai === 'boolean' ? <BoolCell val={row.docai} /> : <span className="text-zinc-400">{row.docai}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-6xl mx-auto px-6 py-16">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold">Simple, transparent pricing</h2>
            <p className="text-zinc-400 mt-1">Start free. Scale when ready. No surprises.</p>
          </div>
          <div className="relative">
            <button
              onClick={() => setShowCurrencyPicker(!showCurrencyPicker)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-300 hover:border-zinc-600 transition-colors"
            >
              {currency} <ChevronDown size={14} />
            </button>
            {showCurrencyPicker && (
              <div className="absolute right-0 mt-1 w-32 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-10 py-1 max-h-60 overflow-y-auto">
                {currencies.map(c => (
                  <button
                    key={c}
                    onClick={() => { setCurrency(c); setShowCurrencyPicker(false) }}
                    className={`w-full text-left px-3 py-1.5 text-sm hover:bg-zinc-700 transition-colors ${c === currency ? 'text-indigo-400 font-medium' : 'text-zinc-300'}`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="grid md:grid-cols-4 gap-5">
          {(plans || []).map(p => {
            const highlight = p.name === 'pro'
            const features = PLAN_FEATURES[p.name] || []
            const label = PLAN_LABELS[p.name] || p.name
            const cta = PLAN_CTA[p.name] || 'Get Started'
            const priceDisplay = p.name === 'enterprise'
              ? 'Custom'
              : p.price?.display || `$${p.price_usd}`
            const period = p.monthly ? '/mo' : ''

            return (
              <div key={p.name} className={`relative p-6 rounded-xl border transition-all ${highlight ? 'bg-indigo-500/5 border-indigo-500/30 ring-1 ring-indigo-500/20 scale-[1.02]' : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'}`}>
                {highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-500 text-white rounded-full">
                    Most Popular
                  </div>
                )}
                <h3 className="font-semibold text-lg">{label}</h3>
                <div className="mt-3 mb-1">
                  <span className="text-3xl font-bold">{priceDisplay}</span>
                  {period && <span className="text-zinc-500 text-sm">{period}</span>}
                </div>
                <ul className="space-y-2 mb-6 mt-4">
                  {features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm text-zinc-300">
                      <CheckCircle size={14} className="text-emerald-400 mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to="/signup" className={`block text-center py-2.5 rounded-lg text-sm font-medium transition-all ${highlight ? 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/25' : 'border border-zinc-700 hover:border-zinc-600 text-zinc-300'}`}>
                  {cta}
                </Link>
              </div>
            )
          })}
        </div>

        {currency !== 'USD' && (
          <p className="text-center text-xs text-zinc-500 mt-6">
            Prices shown in {currency}. Billed in USD at current exchange rates.
          </p>
        )}
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/20 rounded-2xl p-12">
          <h2 className="text-2xl md:text-3xl font-bold">Ready to stop wrestling with documents?</h2>
          <p className="text-zinc-400 mt-3 max-w-xl mx-auto">
            50 free documents. Full pipeline access. No credit card needed.
            See why teams are switching from Textract and Document AI.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link to="/signup" className="px-8 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium text-sm transition-all hover:shadow-lg hover:shadow-indigo-500/25 flex items-center gap-2">
              Start Free <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <FileText className="text-indigo-400" size={18} />
            <span className="text-sm font-semibold"><span className="text-indigo-400">Pix</span>ora</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-zinc-500">
            <span>Built with open-source AI</span>
            <span>OCR + VLM + Jev</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
