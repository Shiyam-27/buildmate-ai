# BuildMate AI — Project Specification

## Concept
BuildMate AI is a conversational chatbot that simplifies the process of building a custom PC. Users describe their requirements in natural language — budget, intended use (gaming, editing, general work), and preferences — and the chatbot responds with a fully compatible, budget-optimized parts list covering CPU, GPU, motherboard, RAM, storage, PSU, and case.

The system combines a large language model, which handles conversation and explains why each component was chosen, with a deterministic compatibility rules engine that validates technical constraints like socket compatibility, RAM support, PSU wattage, and case clearance. This hybrid design ensures recommendations are both easy to understand and technically accurate, addressing a common gap in existing AI-based PC builders that often produce incorrect or unverified suggestions due to relying purely on AI-generated guesses.

## Problem Statement
Building a custom PC requires navigating dozens of interdependent decisions — CPU-motherboard socket compatibility, RAM type/speed support, PSU wattage sufficiency, GPU physical clearance, and budget allocation across components. First-time builders often struggle with this complexity, leading to incompatible purchases, wasted money, or underpowered/overpowered systems. Existing solutions are either vendor-locked or purely LLM-driven without transparent, verifiable compatibility logic — leading to hallucinated specs and silent errors.

## Objective
Design and build a chatbot that takes a user's natural-language requirements and returns a fully compatible, budget-optimized, and explainable custom PC build — combining conversational AI with a deterministic rules engine, so recommendations are both natural to interact with and provably correct.

## Core Features
- **Conversational Intake** — user describes needs in plain language
- **Guided Clarification** — bot asks follow-up questions if info is missing (budget, use case, preferences)
- **Compatibility Engine** — deterministic rule-based validation:
  - CPU socket ↔ motherboard socket
  - RAM type (DDR4/DDR5) ↔ motherboard support
  - PSU wattage ≥ total power draw + headroom (30%)
  - GPU length ↔ case clearance
- **Budget Optimizer** — allocates budget proportionally across component categories based on use case
- **Explainable Recommendations** — every component choice comes with a plain-language reason
- **Alternative/Trade-off Suggestions** — cost-saving swaps with no meaningful performance loss
- **Build Summary Export** — final parts list with total cost, wattage estimate, compatibility confirmation

### Stretch Goals
- Live price fetching (scraping/API from a retailer)
- Save/compare multiple builds
- Upgrade path suggestions for future-proofing
- Voice input

## System Architecture
```
User (Chat UI)
      │
      ▼
Frontend (Streamlit / React)
      │
      ▼
Backend (FastAPI)
   ├── Intent & Slot Extraction (LLM) → parses budget, use case, preferences
   ├── Compatibility Rules Engine (Python) → validates socket/RAM/PSU/case logic
   ├── Budget Allocation Logic → distributes budget across categories
   ├── Component Database (JSON/CSV dataset)
   └── LLM Layer (NVIDIA NIM API) → natural conversation + explanation generation
      │
      ▼
Response: Structured build + natural-language explanation
```

**Key design principle:** The LLM handles conversation and explanation. The rules engine handles correctness. This avoids the hallucination problem seen in pure-LLM competitors.

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| LLM | NVIDIA NIM API (OpenAI-compatible interface, hosted via build.nvidia.com) |
| LLM Client Library | `openai` Python package, pointed at NVIDIA's base_url |
| LLM Model | meta/llama-3.3-70b-instruct (or another NIM-hosted model of choice) |
| Compatibility Logic | Plain Python (rule-based) |
| Component Data | Curated JSON/CSV dataset |
| Frontend | Streamlit (MVP) |
| Optional Storage | SQLite for saved builds/chat history |

## NVIDIA NIM Integration Details
- **Base URL:** `https://integrate.api.nvidia.com/v1`
- **Auth:** `NVIDIA_API_KEY` (stored in `.env`, never hardcoded or committed to git)
- **Client:** Standard `openai` Python package, configured with NVIDIA's base_url and API key, since NIM exposes an OpenAI-compatible `/chat/completions` endpoint
- **Model:** `meta/llama-3.3-70b-instruct` (swappable with any other NIM-hosted chat model from the API Catalog)
- **Usage in project:** Two LLM calls only —
  1. `extract_intent()` — parses user's natural-language message into structured JSON (budget, use_case, preferences)
  2. `generate_explanation()` — writes plain-language reasoning for the recommended parts list
- **Note:** NVIDIA's hosted API Catalog is intended for prototyping/evaluation; production deployment terms depend on NVIDIA AI Enterprise licensing if this project is ever scaled beyond a student/portfolio project.

## Component Dataset Schema
- **CPUs**: name, socket, price, tdp, core_count
- **Motherboards**: name, socket, ram_type, form_factor, price
- **RAM**: type, speed, capacity, price
- **GPUs**: name, tdp, length_mm, price, performance_tier
- **PSUs**: wattage, price, efficiency_rating
- **Cases**: max_gpu_length_mm, form_factor, price
- **Storage**: type (NVMe/SATA), capacity, price

## Build Roadmap
1. Component dataset (JSON files, 15-20 entries per category)
2. Compatibility rules engine (Python, with unit tests)
3. Budget allocation logic
4. LLM integration via NVIDIA NIM API (intent extraction + explanation generation)
5. FastAPI endpoint wiring (/build)
6. Streamlit frontend
7. Edge case testing (low budget, conflicting requirements, missing info)
8. Documentation (README + project report)

## Evaluation Metrics
- Compatibility accuracy — % of generated builds passing all rule checks
- Budget adherence — how close final build cost is to stated budget
- User satisfaction — clarity of explanations
- Response coherence — naturalness of multi-turn clarification flow

## Why This Project Stands Out
Unlike existing tools (Newegg PC Builder, MSI EZ PC Builder) which are either vendor-locked or LLM-only, this project's differentiator is the hybrid architecture: deterministic compatibility logic + conversational LLM layer. It demonstrates understanding of when not to trust an LLM and how to combine symbolic logic with generative AI.
