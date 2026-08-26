# 🖥️ BuildMate AI

> A conversational AI-powered PC builder chatbot — hybrid architecture combining a deterministic compatibility rules engine with NVIDIA's LLM API for natural language understanding and explanation.

---

## ✨ Features

- **Natural language intake** — just describe what you need in plain English/Hindi
- **Multi-turn conversation** — refine your requirements across multiple messages
- **Budget optimiser** — allocates budget across components based on use case (gaming → GPU-heavy, editing → CPU+RAM-heavy)
- **Deterministic compatibility checks**:
  - CPU socket ↔ Motherboard socket
  - RAM type (DDR4/DDR5) ↔ Motherboard support
  - PSU wattage ≥ total TDP × 1.30 headroom
  - GPU length ≤ Case max clearance
- **LLM-generated explanations** — friendly, plain-language reasoning for every component choice
- **All prices in INR (₹)**

---

## 🏗️ Architecture

```
User (Streamlit UI)
      │
      ▼
  app.py  (Streamlit — port 8501)
      │  HTTP POST /build
      ▼
  api/main.py  (FastAPI — port 8000)
      ├── extract_intent()          →  NVIDIA NIM LLM  →  {budget, use_case, preferences}
      ├── allocate_budget_and_select_components()  →  engine/budget.py
      ├── validate_build_compatibility()           →  engine/compatibility.py
      └── generate_explanation()   →  NVIDIA NIM LLM  →  natural language
      │
      ▼
  data/*.json  (Component database — 7 categories, INR pricing)
```

---

## 🚀 Setup & Running

### 1. Prerequisites

- Python 3.10+
- A valid [NVIDIA NIM API key](https://build.nvidia.com/) (free tier available)

### 2. Clone and install

```bash
# From the buildmateAi directory:
pip install -r requirements.txt
```

### 3. Configure environment

Edit `.env` (already exists) and make sure it contains:

```env
NVIDIA_API_KEY=your_nvidia_nim_api_key_here
NVIDIA_MODEL=nvidia/nemotron-3-super-120b-a12b
```

> ⚠️ `.env` is in `.gitignore` — it will never be committed to git.

### 4. Start the FastAPI backend

Open a terminal in the `buildmateAi/` directory and run:

```bash
uvicorn api.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 5. Start the Streamlit frontend

Open a **second** terminal in the same directory and run:

```bash
streamlit run app.py
```

The browser will open automatically at `http://localhost:8501`.

---

## 💬 Usage

Type your requirements in the chat box, for example:

- *"Gaming PC under ₹80,000"*
- *"Video editing workstation ₹1.5 lakh, prefer AMD"*
- *"General purpose college PC for ₹40,000"*
- *"Budget gaming build ₹60,000 with NVIDIA GPU"*

The bot will:
1. Extract your budget, use case, and preferences
2. Select the best components within your budget
3. Validate all compatibility constraints
4. Explain every choice in plain language

---

## 📁 Project Structure

```
buildmateAi/
├── app.py                  # Streamlit frontend
├── requirements.txt        # Python dependencies
├── .env                    # API key (never committed)
├── .gitignore
├── README.md               # This file
│
├── api/
│   └── main.py             # FastAPI backend (intent extraction, /build endpoint)
│
├── engine/
│   ├── budget.py           # Budget allocation + component selection
│   ├── compatibility.py    # Hardware compatibility rules
│   ├── budget_demo.py      # Demo script
│   └── demo.py             # General demo
│
└── data/                   # Component database (JSON, INR pricing)
    ├── cpus.json           # 30 CPUs (AMD Ryzen 5000/7000 + Intel 12th/13th Gen)
    ├── gpus.json           # 20 GPUs (RTX 30/40 series + RX 6000/7000)
    ├── motherboards.json   # AM4, AM5, LGA1700 — DDR4 & DDR5
    ├── ram.json
    ├── psus.json
    ├── cases.json
    └── storage.json
```

---

## 🔧 Running Unit Tests

```bash
# Test the budget engine (run from buildmateAi/ directory)
python engine/budget.py

# Test the compatibility engine
python engine/compatibility.py
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Frontend | Streamlit |
| LLM | NVIDIA NIM API (`nvidia/nemotron-3-super-120b-a12b`) |
| LLM Client | `openai` Python package (OpenAI-compatible interface) |
| Compatibility Logic | Plain Python (deterministic rules) |
| Component Data | Curated JSON files |

---

## ⚠️ Known Limitations

- Component dataset is static (no live price fetching)
- Only supports INR pricing
- LLM response time depends on NVIDIA NIM API latency (~5-20 seconds)

---

## 🗺️ Roadmap

- [ ] Live price fetching from Indian retailers (Amazon, Flipkart, MDComputers)
- [ ] Save and compare multiple builds
- [ ] Upgrade path suggestions
- [ ] User accounts and build history

---

*Built with FastAPI, Streamlit, and the NVIDIA NIM API.*
