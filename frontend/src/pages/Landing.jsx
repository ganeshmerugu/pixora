import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Zap, Shield, Brain, BarChart3, Globe, CheckCircle, ArrowRight, ChevronDown, Sun, Moon } from 'lucide-react'
import { useTheme } from '../auth/ThemeContext'

const FEATURES = [
  { icon: Brain, title: 'AI-Powered OCR', desc: 'Multi-engine OCR with Tesseract, Surya, and Claude Vision. Handles handwriting, tables, and 80+ languages.' },
  { icon: Zap, title: 'Smart Extraction', desc: 'Extracts structured data from invoices, medical records, contracts, and more with self-correcting AI agents.' },
  { icon: Shield, title: 'Grounding Verification', desc: 'Every extracted value is verified against the source document. Zero hallucinations guaranteed.' },
  { icon: BarChart3, title: 'Quality Scoring', desc: '8-dimension quality scoring with adaptive thresholds. Know exactly how confident the extraction is.' },
  { icon: Globe, title: 'Multi-Language', desc: 'Auto-detects document language and routes to the best OCR engine. Supports 80+ languages out of the box.' },
  { icon: CheckCircle, title: 'Human-in-the-Loop', desc: 'Low-confidence fields are flagged for review. Corrections feed back into the system to improve over time.' },
]

const PLAN_FEATURES = {
  'free_trial': ['Basic OCR (Tesseract)', 'Heuristic extraction', 'Quality scoring', 'API access'],
  'starter': ['Everything in Free', 'AI extraction (Groq)', 'Multi-language OCR', 'Priority support'],
  'pro': ['Everything in Starter', 'Vision AI (Qwen VL)', 'Table extraction', 'HITL workflow', 'Webhooks'],
  'enterprise': ['Everything in Pro', 'Claude/GPT-4V quality', 'SSO/SAML', 'Dedicated support', 'Custom SLA'],
}

const PLAN_CTA = { 'free_trial': 'Start Free', 'starter': 'Get Started', 'pro': 'Go Pro', 'enterprise': 'Contact Us' }
const PLAN_LABELS = { 'free_trial': 'Free Trial', 'starter': 'Starter', 'pro': 'Pro', 'enterprise': 'Enterprise' }

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

export default function Landing() {
  const { theme, toggle: toggleTheme } = useTheme()
  const [currency, setCurrency] = useState(detectCurrency)
  const [plans, setPlans] = useState(null)
  const [currencies, setCurrencies] = useState([])
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false)

  useEffect(() => {
    fetch(`/api/v1/billing/plans?currency=${currency}`)
      .then(r => r.json())
      .then(data => {
        setPlans(data.plans)
        if (data.supported_currencies) {
          setCurrencies(data.supported_currencies)
        }
      })
      .catch(() => {})
  }, [currency])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      {/* Nav */}
      <nav className="border-b border-zinc-800/50 sticky top-0 bg-zinc-950/80 backdrop-blur z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <FileText className="text-indigo-400" size={24} />
            <span className="text-lg font-bold"><span className="text-indigo-400">Pix</span>ora</span>
          </Link>
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
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <div className="inline-block px-3 py-1 mb-6 text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full">
          Now in public beta
        </div>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-tight">
          Turn any document into<br />
          <span className="text-indigo-400">structured data</span>
        </h1>
        <p className="mt-6 text-lg text-zinc-400 max-w-2xl mx-auto">
          AI-powered document intelligence that extracts, classifies, and understands invoices, medical records, contracts, and more. Self-correcting agents ensure accuracy.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link to="/signup" className="px-6 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium text-sm transition-colors flex items-center gap-2">
            Start Free Trial <ArrowRight size={16} />
          </Link>
          <Link to="/login" className="px-6 py-3 border border-zinc-700 hover:border-zinc-600 text-zinc-300 rounded-lg text-sm transition-colors">
            Sign in
          </Link>
        </div>
        <p className="mt-4 text-xs text-zinc-500">50 documents free. No credit card required.</p>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-center mb-12">Everything you need for document intelligence</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors">
              <Icon className="text-indigo-400 mb-3" size={24} />
              <h3 className="font-semibold mb-2">{title}</h3>
              <p className="text-sm text-zinc-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h2 className="text-2xl font-bold">Simple, transparent pricing</h2>
            <p className="text-zinc-400 mt-1">Start free, scale as you grow</p>
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

        <div className="grid md:grid-cols-4 gap-6">
          {(plans || []).map(p => {
            const highlight = p.name === 'pro'
            const features = PLAN_FEATURES[p.name] || []
            const label = PLAN_LABELS[p.name] || p.name
            const cta = PLAN_CTA[p.name] || 'Get Started'
            const priceDisplay = p.name === 'enterprise'
              ? 'Custom'
              : p.price?.display || `$${p.price_usd}`
            const period = p.monthly ? '/month' : ''

            return (
              <div key={p.name} className={`p-6 rounded-xl border ${highlight ? 'bg-indigo-500/5 border-indigo-500/30 ring-1 ring-indigo-500/20' : 'bg-zinc-900/50 border-zinc-800'}`}>
                {highlight && <div className="text-xs font-medium text-indigo-400 mb-3">Most Popular</div>}
                <h3 className="font-semibold text-lg">{label}</h3>
                <div className="mt-3 mb-1">
                  <span className="text-3xl font-bold">{priceDisplay}</span>
                  {period && <span className="text-zinc-500 text-sm">{period}</span>}
                </div>
                <p className="text-sm text-zinc-400 mb-6">
                  {p.docs_limit >= 999999 ? 'Unlimited documents' : `${p.docs_limit.toLocaleString()} documents${p.monthly ? '/month' : ' total'}`}
                </p>
                <ul className="space-y-2 mb-6">
                  {features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm text-zinc-300">
                      <CheckCircle size={14} className="text-emerald-400 mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to="/signup" className={`block text-center py-2.5 rounded-lg text-sm font-medium transition-colors ${highlight ? 'bg-indigo-500 hover:bg-indigo-600 text-white' : 'border border-zinc-700 hover:border-zinc-600 text-zinc-300'}`}>
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

        <div className="mt-16">
          <h3 className="text-xl font-bold text-center mb-2">Accuracy SLA Guarantees</h3>
          <p className="text-zinc-400 text-center text-sm mb-8">Pay by accuracy, not just volume. Every extraction comes with provenance proof.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { name: 'Standard', target: '85%', price: '$0.01/doc', features: ['Cheapest available provider', 'Best-effort accuracy', 'Basic quality report'], color: 'zinc' },
              { name: 'Premium', target: '95%', price: '$0.03/doc', features: ['Best provider + corrections', 'Full grounding evidence', 'Compliance audit export'], color: 'indigo' },
              { name: 'Guaranteed', target: '99%', price: '$0.10/doc', features: ['Max corrections + human review', 'Tamper-evident audit trail', 'Regulatory-grade provenance'], color: 'emerald' },
            ].map(sla => (
              <div key={sla.name} className={`p-6 rounded-xl border ${sla.color === 'indigo' ? 'bg-indigo-500/5 border-indigo-500/30' : sla.color === 'emerald' ? 'bg-emerald-500/5 border-emerald-500/30' : 'bg-zinc-900/50 border-zinc-800'}`}>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold">{sla.name}</h4>
                  <span className={`text-2xl font-bold ${sla.color === 'indigo' ? 'text-indigo-400' : sla.color === 'emerald' ? 'text-emerald-400' : 'text-zinc-300'}`}>{sla.target}</span>
                </div>
                <p className="text-sm text-zinc-500 mb-4">{sla.price}</p>
                <ul className="space-y-2">
                  {sla.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm text-zinc-300">
                      <CheckCircle size={14} className="text-emerald-400 mt-0.5 shrink-0" />{f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 mt-16">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <FileText className="text-indigo-400" size={18} />
            <span className="text-sm font-semibold"><span className="text-indigo-400">Pix</span>ora</span>
          </div>
          <p className="text-xs text-zinc-500">Built with AI. Powered by open-source models.</p>
        </div>
      </footer>
    </div>
  )
}
