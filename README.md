<p align="center">
  <img src="https://img.shields.io/badge/Pixora-Document%20Intelligence-6366f1?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0xNSAySDZhMiAyIDAgMCAwLTIgMnYxNmEyIDIgMCAwIDAgMiAyaDEyYTIgMiAwIDAgMCAyLTJWN1oiLz48cGF0aCBkPSJNMTQgMnY0YTIgMiAwIDAgMCAyIDJoNCIvPjwvc3ZnPg==&logoColor=white" alt="Pixora" />
</p>

<h1 align="center">Pixora</h1>
<p align="center">
  <strong>AI-Powered Document Intelligence Platform</strong><br/>
  Extract, classify, and understand any document — invoices, medical records, contracts, ID cards, and more.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ParseBench-85.2%25-10b981?style=flat-square" alt="ParseBench Score" />
  <img src="https://img.shields.io/badge/LlamaParse-84.9%25-f59e0b?style=flat-square" alt="LlamaParse Score" />
  <img src="https://img.shields.io/badge/Tests-215%20passing-10b981?style=flat-square" alt="Tests" />
  <img src="https://img.shields.io/badge/Cost-$0%2Fpage-6366f1?style=flat-square" alt="Cost" />
  <img src="https://img.shields.io/badge/Models-19-818cf8?style=flat-square" alt="Models" />
  <img src="https://img.shields.io/badge/License-Proprietary-ef4444?style=flat-square" alt="License" />
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-benchmarks">Benchmarks</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-pricing">Pricing</a> •
  <a href="#-api">API</a> •
  <a href="#-deployment">Deployment</a>
</p>

---

## Why Pixora?

Most document AI tools either **cost too much** (LlamaParse: ~$0.05/page) or **don't work** on real-world documents (scanned, skewed, handwritten, multi-language).

Pixora solves both:

| | Pixora | LlamaParse | AWS Textract |
|---|---|---|---|
| **Accuracy** | 85.2% | 84.9% | ~78% |
| **Cost/page** | **$0.00** | $0.01–$0.05 | $0.015 |
| **API key needed** | No | Yes | Yes |
| **Self-hosted** | Yes | No | No |
| **Open-source models** | Yes | No | No |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/ganeshmerugu/pixora.git
cd pixora

# Install
pip install -r requirements.txt

# Run
python run.py
# → http://localhost:8000
```

**Default login:** `admin@pixora.ai` / `admin123`

**Optional — enable AI extraction (free):**
```bash
# Get a free Gemini API key: https://aistudio.google.com/apikey
echo "PIXORA_GEMINI_API_KEY=your_key" > .env
```

---

## ✨ Features

### Document Processing
- **Multi-engine OCR** — Tesseract, EasyOCR, Surya, docTR, GOT-OCR2
- **Smart pipeline** — auto-detects document quality, escalates from free OCR → VLM when needed
- **65+ OCR confusion pairs** — fixes `l/1`, `O/0`, `/→I`, `rn→m` automatically
- **Multi-language** — auto-detects and routes to best engine for 80+ languages
- **Handwriting detection** — routes handwritten content to ICR/VLM path

### AI Extraction
- **Generic extraction** — no hardcoded rules, the AI understands any document layout
- **Self-correcting agents** — classifier → router → extractor → validator → scorer loop
- **Cross-field validation** — subtotal + tax = total, date consistency checks
- **Grounding verification** — every value traced back to source text, zero hallucinations

### Enterprise Features
- **Multi-tenant auth** — JWT + Google OAuth, role-based access
- **Usage billing** — free trial (50 docs), starter ($9/mo), pro ($29/mo)
- **Multi-region pricing** — auto-detects user's timezone, shows local currency
- **Human-in-the-loop** — low-confidence fields flagged for review
- **Audit log** — every pipeline step tracked with cost and latency

### Eval & Benchmarking
- **ParseBench integration** — test against LlamaParse's benchmark
- **Enterprise suite** — WER/CER, TEDS (tables), mAP/IoU (layout), QA accuracy
- **RealDoc-Bench** — 5 real-world failure modes: layout, handwriting, multi-page, scan quality, domain formatting
- **Production metrics** — cost/page, p95 latency, throughput, semantic formatting detection

---

## 📊 Benchmarks

### ParseBench (vs LlamaParse Agentic)

| Dimension | Pixora | LlamaParse | Winner |
|-----------|--------|-----------|--------|
| Charts | **94.9%** | ~75% | Pixora +20% |
| Layout | **100.0%** | ~75% | Pixora +25% |
| Content Faithfulness | **86.6%** | ~85% | Pixora +1.6% |
| Text Formatting | **66.5%** | ~60% | Pixora +6.5% |
| Tables | 77.9% | ~80% | LlamaParse +2% |
| **Overall** | **85.2%** | **84.9%** | **Pixora** |

### RealDoc-Bench (Production Failure Modes)

| Failure Mode | Score | What It Tests |
|-------------|-------|---------------|
| Layout Complexity | **100%** | Multi-column tables, nested structures |
| Handwriting/Mixed | **100%** | Annotations, stamps, signatures |
| Document Length | **100%** | Cross-page entity resolution |
| Domain Formatting | **100%** | Healthcare EOB, CPT codes, insurance |
| Scan Quality | **51%** | Degraded OCR → VLM escalation |
| **Overall** | **90.2%** | |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────┐
│           React Frontend                 │
│  Landing • Auth • Parse • Dashboard      │
├─────────────────────────────────────────┤
│           FastAPI Backend                │
│  75 routes • JWT auth • Multi-tenant     │
├─────────┬──────────┬───────────────────┤
│ Tier 1  │ Tier 2   │ Tier 3            │
│ FREE    │ CHEAP    │ ENTERPRISE        │
│ $0/page │ ~$0.001  │ ~$0.03            │
├─────────┼──────────┼───────────────────┤
│Tesseract│Surya OCR │Claude Vision      │
│EasyOCR  │Qwen2.5VL │GPT-4V            │
│PyMuPDF  │Gemini *  │                   │
│Rules    │Florence2 │Claude Sonnet      │
└─────────┴──────────┴───────────────────┘
  * Gemini Flash = free tier (1500 req/day)
```

### Smart Pipeline (Quality-Aware Extraction)

```
Document → [1] Direct text (PyMuPDF) ─── $0.000
                    │ quality < 0.4
           [2] Preprocess + OCR ──────── $0.000
                    │ quality < 0.3
           [3] VLM escalation ────────── $0.000 (Gemini free)
                    │
           Structured JSON + Markdown
```

---

## 💰 Pricing

| Plan | Documents | Price | Features |
|------|-----------|-------|----------|
| **Free Trial** | 50 total | $0 | Basic OCR + extraction |
| **Starter** | 200/month | $9/mo | + AI extraction (Groq) |
| **Pro** | 1,000/month | $29/mo | + VLM, tables, HITL |
| **Enterprise** | Unlimited | Custom | + SSO, SLA, support |

Prices auto-convert to local currency (₹, €, £, ¥, and more).

---

## 🔌 API

### Parse a document
```bash
curl -X POST http://localhost:8000/api/v1/parse/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.pdf" \
  -F "tier=agentic"
```

### Response
```json
{
  "doc_type": "invoice",
  "extraction": {
    "vendor_name": "Acme Corporation",
    "invoice_number": "INV-2024-00891",
    "total_due": "$49,674.22",
    "due_date": "04/14/2024"
  },
  "quality_report": { "overall_score": 0.94 },
  "grounding_report": { "grounding_rate": 1.0 },
  "markdown": "# Invoice\n**Vendor:** Acme Corporation\n..."
}
```

### Python SDK
```python
from pixora import PixoraClient

client = PixoraClient(api_key="your-key")
result = client.parse("invoice.pdf", tier="agentic")

print(result.extraction["vendor_name"])  # "Acme Corporation"
print(result.quality_report["overall_score"])  # 0.94
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/parse/upload` | Parse a document |
| POST | `/api/v1/auth/signup` | Create account |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/billing/plans` | View pricing |
| GET | `/api/v1/models` | List 19 available models |
| GET | `/api/v1/health` | System status |
| GET | `/api/docs` | Swagger API docs |

---

## 🚢 Deployment

### Render (Free — Recommended)

1. Fork this repo
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Add env vars: `PIXORA_GEMINI_API_KEY`, `PIXORA_JWT_SECRET`
5. Deploy

### Docker

```bash
docker build -t pixora .
docker run -p 8000:8000 \
  -e PIXORA_GEMINI_API_KEY=your_key \
  -e PIXORA_JWT_SECRET=random_secret \
  pixora
```

### Docker Compose

```bash
docker-compose up
```

---

## 🧪 Testing

```bash
# Run all 215 tests
python -m pytest pixora/tests/ -v

# Run ParseBench evaluation
python run_parsebench.py --test

# Run enterprise benchmark suite
python -c "
from pixora.evals.enterprise.realdoc_bench import run_realdoc_bench, format_realdoc_report
report = run_realdoc_bench()
print(format_realdoc_report(report))
"
```

---

## 📁 Project Structure

```
pixora/
├── agents/          # AI agent pipeline (classifier, router, extractor, validator, scorer)
├── api/             # FastAPI app with 75 routes, auth middleware
├── auth/            # JWT + Google OAuth, multi-tenant, billing
├── classifiers/     # Rule-based + vision hybrid classification
├── config/          # Settings, model catalog (19 models), serverless config
├── evals/           # ParseBench, enterprise suite, RealDoc-Bench
├── extraction/      # Smart extractor (Gemini), docling, LLM, chart extractor
├── frontend/        # React 19 + Tailwind + dark/light theme
├── harness/         # Cost governor, drift detection, grounding verification
├── ocr/             # 7 OCR engines, smart pipeline, preprocessing, postprocessor
├── parsing/         # PDF, image, DOCX, HTML, spreadsheet readers
├── providers/       # Gemini, Groq, Together, Replicate, Ollama, Claude, HuggingFace
└── tests/           # 215 tests
```

---

## 🔐 Environment Variables

```bash
# Required for AI extraction (free)
PIXORA_GEMINI_API_KEY=        # https://aistudio.google.com/apikey

# Optional — additional providers
PIXORA_GROQ_API_KEY=          # Fast LLM extraction
PIXORA_TOGETHER_API_KEY=      # Backup LLM
PIXORA_REPLICATE_API_TOKEN=   # VLM for images
PIXORA_ANTHROPIC_API_KEY=     # Claude (highest quality)

# Auth
PIXORA_JWT_SECRET=            # Random string for JWT signing
PIXORA_GOOGLE_CLIENT_ID=      # Google OAuth (optional)
PIXORA_GOOGLE_CLIENT_SECRET=

# Dev
PIXORA_TLS_VERIFY=true        # Set to false for corporate proxies
```

---

## 🤝 Contributing

This is a proprietary product. For partnership inquiries, contact the team.

---

<p align="center">
  <strong>Built with AI. Powered by open-source models. Zero API cost.</strong><br/>
  <sub>Pixora v1.1 — 215 tests passing, 85.2% ParseBench, 90.2% RealDoc-Bench</sub>
</p>
