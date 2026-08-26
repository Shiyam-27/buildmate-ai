from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import os
import json
import re
import openai

# ── Engine imports ─────────────────────────────────────────────────────────────
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "engine"))

from budget import allocate_budget_and_select_components
from compatibility import (
    check_cpu_motherboard_compatibility,
    check_ram_type_compatibility,
    check_psu_wattage_sufficiency,
    check_gpu_case_compatibility,
    validate_build_compatibility,
)
from analytics import (
    calculate_power_analysis,
    calculate_bottleneck_analysis,
    find_cost_saving_alternatives,
    generate_retailer_links,
)

# ── Load environment ────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── FastAPI app ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="BuildMate AI",
    description="AI-powered custom PC builder with deterministic compatibility checking",
    version="1.0.0",
)

# Allow Streamlit (and any local origin) to call the API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── NVIDIA NIM client ───────────────────────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
MODEL_NAME     = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

if not NVIDIA_API_KEY:
    print("WARNING: NVIDIA_API_KEY is not set. LLM features will fail.")

client = openai.OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY or "dummy",   # openai client requires a non-empty string
)


# ── Pydantic models ─────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str     # 'user' or 'assistant'
    content: str

class BuildRequest(BaseModel):
    conversation:  Optional[List[Message]]      = None
    user_message:  Optional[str]                = None
    budget:        Optional[float]              = None
    use_case:      Optional[str]                = None
    preferences:   Optional[Dict[str, Any]]     = None
    current_build: Optional[Dict[str, Any]]     = None


# ── Helper: strip markdown code fences from LLM output ─────────────────────────
def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def sanitize_llm_text(text: str) -> str:
    """
    Sanitize generated text to ensure words like 'rupee', 'rupees', 'India', etc.
    never appear in user-facing output, converting them to 'price', 'cost', or removing them.
    """
    if not text:
        return text

    # Common phrasing replacements
    text = re.sub(r'(?i)\bperformance\s+per\s+rupees?\b', 'price-to-performance', text)
    text = re.sub(r'(?i)\bper\s+rupees?\b', 'for the price', text)
    text = re.sub(r'(?i)\bvalue\s+for\s+rupees?\b', 'value for money', text)
    text = re.sub(r'(?i)\bevery\s+rupees?\b', 'every penny', text)
    text = re.sub(r'(?i)\bsave\s+rupees?\b', 'save money', text)

    # Standalone mentions
    text = re.sub(r'(?i)\bin\s+india\b', '', text)
    text = re.sub(r'(?i)\bindia\b', '', text)
    text = re.sub(r'(?i)\brupees?\b', 'price', text)
    text = re.sub(r'(?i)\binr\b', '₹', text)

    # Clean double spaces and spaces before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


# ── Intent extraction ───────────────────────────────────────────────────────────
def extract_intent(
    user_message: str,
    prev_budget:      Optional[float]          = None,
    prev_use_case:    Optional[str]            = None,
    prev_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract budget, use_case, and preferences from user message using LLM,
    then merge with previously known values (multi-turn state persistence).

    Returns dict with keys: budget, use_case, preferences.
    On failure, returns dict with an additional 'error' key.
    """
    system_prompt = """
You are an AI assistant that extracts PC building requirements from user input.
Return ONLY a valid JSON object — no explanations, no markdown fences.

Fields to extract:
- "budget": number representing total budget (null if not specified).
             Accept ranges like "under 80000" or "around 1 lakh" — convert to a number.
- "use_case": one of "gaming", "editing", or "general" (null if not specified).
- "preferences": object with optional keys:
    - "cpu_brand": "AMD" or "Intel" (only if user specifies)
    - "cpu_model": string of specific CPU model if user mentions one (e.g. "5900X", "Ryzen 5 7600", "i5-13400F")
    - "gpu_brand": "NVIDIA" or "AMD" (only if user specifies)
    - "gpu_model": string of specific GPU model if user mentions one (e.g. "5070", "4070", "3060 Ti", "RX 7800 XT")
    - "ram_type": "DDR4" or "DDR5" (only if user specifies)
  Use null or {} if no preferences mentioned.

IMPORTANT: Return null for any field the user did NOT specify — do not guess defaults.

Examples:
User: "gaming PC under 80000, prefer AMD"
Output: {"budget": 80000, "use_case": "gaming", "preferences": {"cpu_brand": "AMD"}}

User: "upgrade the gpu with 5070"
Output: {"budget": null, "use_case": null, "preferences": {"gpu_brand": "NVIDIA", "gpu_model": "5070"}}

User: "editing workstation 1.5 lakh budget"
Output: {"budget": 150000, "use_case": "editing", "preferences": {}}

User: "general use, 50k"
Output: {"budget": 50000, "use_case": "general", "preferences": {}}
""".strip()

    def _parse_response(raw: str) -> Optional[Dict]:
        cleaned = _strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _normalize_and_merge(parsed: Dict) -> Dict[str, Any]:
        # Budget
        budget = parsed.get("budget")
        if budget is not None:
            try:
                budget = float(budget)
            except (ValueError, TypeError):
                budget = None

        # Use case
        use_case = parsed.get("use_case")
        if use_case not in ("gaming", "editing", "general", None):
            use_case = None

        # Preferences
        prefs = parsed.get("preferences")
        if not isinstance(prefs, dict):
            prefs = {}

        # Merge with previous turn values
        merged_budget   = budget   if budget   is not None else prev_budget
        merged_use_case = use_case if use_case is not None else prev_use_case
        merged_prefs    = dict(prev_preferences or {})
        merged_prefs.update(prefs)

        if merged_use_case is None:
            merged_use_case = "general"   # safe default

        return {
            "budget":      merged_budget,
            "use_case":    merged_use_case,
            "preferences": merged_prefs,
        }

    # First attempt
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = _parse_response(raw)
        if parsed is not None:
            return _normalize_and_merge(parsed)

        print(f"[extract_intent] First attempt failed to parse: {raw[:200]}")

        # Second attempt with a stricter prompt
        strict_prompt = system_prompt + "\n\nIMPORTANT: Output ONLY the JSON object. Nothing else."
        resp2 = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": strict_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        raw2 = resp2.choices[0].message.content.strip()
        parsed2 = _parse_response(raw2)
        if parsed2 is not None:
            return _normalize_and_merge(parsed2)

        return {
            "budget": None, "use_case": None, "preferences": {},
            "error": f"Could not parse LLM response. Raw: {raw[:200]}",
        }

    except openai.AuthenticationError:
        return {
            "budget": None, "use_case": None, "preferences": {},
            "error": "Invalid NVIDIA API key. Please check your .env file.",
        }
    except openai.RateLimitError:
        return {
            "budget": None, "use_case": None, "preferences": {},
            "error": "NVIDIA API rate limit reached. Please wait a moment and try again.",
        }
    except Exception as e:
        return {
            "budget": None, "use_case": None, "preferences": {},
            "error": f"LLM request failed: {str(e)}",
        }


# ── Intent Router (Modify vs Q&A Question) ──────────────────────────────────────
def classify_intent(user_message: str, has_existing_build: bool) -> str:
    """
    Determine if user wants to modify their build / swap parts,
    or is asking a conversational question about the current build.
    """
    if not has_existing_build:
        return "modify"

    system_prompt = """You are an AI intent router for a custom PC builder assistant.
An active PC build has already been recommended to the user.
Classify the user's latest message into EXACTLY ONE category:

1. "modify": The user wants to change, swap, or upgrade/downgrade components, switch brands (e.g. Intel to AMD, AMD to NVIDIA), change budget (e.g. "make it 70k", "increase budget to 1 lakh"), or rebuild.
   Examples:
   - "can you change the processor from intel to amd"
   - "switch to DDR5 RAM"
   - "reduce budget to 60000"
   - "use an NVIDIA GPU instead"
   - "make it cheaper"

2. "question": The user is asking a question about the existing build, inquiring why a part was chosen, asking about game performance/FPS, cooling, compatibility, upgrade paths, or general conversation.
   Examples:
   - "why are we using intel instead of amd?"
   - "will this run Cyberpunk at 60fps in 1080p?"
   - "is 550W PSU enough for this system?"
   - "what games can this build handle?"
   - "can I add more storage later?"
   - "tell me more about this graphics card"

Output ONLY a JSON object: {"intent": "modify"} or {"intent": "question"}."""

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        cleaned = _strip_code_fences(resp.choices[0].message.content)
        parsed = json.loads(cleaned)
        return parsed.get("intent", "question")
    except Exception as e:
        print(f"[classify_intent] Fallback due to: {e}")
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["why", "what", "how", "can it", "will it", "is it", "explain", "tell me"]):
            return "question"
        if any(w in msg_lower for w in ["change", "switch", "replace", "swap", "make it", "prefer", "instead", "upgrade", "downgrade"]):
            return "modify"
        return "question"


def answer_build_question(
    user_message: str,
    current_build: Dict[str, Any],
    conversation: Optional[List[Message]] = None,
) -> str:
    """
    Answer user's conversational question with full context of the active PC build.
    """
    build_data = current_build.get("build") or current_build
    selected = build_data.get("selected_components", {})
    total_cost = build_data.get("total_cost", 0)
    remain = build_data.get("remaining_budget", 0)

    def _comp(k):
        c = selected.get(k)
        if isinstance(c, dict) and c:
            return f"{c.get('name', 'Unknown')} (Price: ₹{c.get('price', 0):,})"
        return "Not selected"

    context = f"""ACTIVE PC BUILD:
- CPU: {_comp('cpu')}
- GPU: {_comp('gpu')}
- Motherboard: {_comp('motherboard')}
- RAM: {_comp('ram')}
- Storage: {_comp('storage')}
- PSU: {_comp('psu')}
- Case: {_comp('case')}
- Total Cost: ₹{total_cost:,.0f}
- Remaining Budget: ₹{remain:,.0f}
"""

    system_prompt = f"""You are BuildMate AI, a friendly, highly knowledgeable PC building expert and advisor.
You are chatting with a user about their recommended custom PC build.

{context}

Guidelines:
- Answer the user's specific question directly, concisely, and helpfully using markdown.
- When asked "why" a component was chosen (e.g. why Intel instead of AMD), explain the exact price-to-performance, budget allocation, and platform balance reasons in a natural conversational tone.
- If the user asks about gaming performance, FPS, video editing, or upgradeability, give realistic, accurate advice tailored to the exact specs of this build.
- If they want to change parts, encourage them and let them know they can ask you to swap or adjust any component anytime!
- Keep your answer friendly and engaging, like chatting with ChatGPT or Gemini.
- STRICT RULE: Never mention any country name (never say "India", "in India", or any country) and never write currency names in words (never say "rupee", "rupees", "INR", or "bucks"). When referring to cost or value, write only the number with the '₹' symbol (e.g. "₹80,000" or "price-to-performance ratio")."""

    messages = [{"role": "system", "content": system_prompt}]
    if conversation:
        for m in conversation[-6:]:
            messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return sanitize_llm_text(resp.choices[0].message.content.strip())
    except Exception as e:
        return sanitize_llm_text(
            f"I encountered an error answering your question: {str(e)}. "
            "Regarding your build, feel free to ask me to change any component (like switching to AMD or increasing budget) anytime!"
        )


# ── Explanation generation ──────────────────────────────────────────────────────
def generate_explanation(build: Dict[str, Any]) -> str:
    """
    Generate a natural-language explanation for the recommended build using the LLM.
    Falls back to a template string if the LLM call fails.
    """
    selected = build.get("selected_components", {})
    total_cost       = build.get("total_cost", 0)
    remaining_budget = build.get("remaining_budget", 0)

    def _get(key, field, fallback="Unknown"):
        comp = selected.get(key)
        return comp.get(field, fallback) if isinstance(comp, dict) and comp else fallback

    cpu_desc      = f"{_get('cpu', 'name')} ({_get('cpu', 'core_count', 0)} cores)"
    gpu_desc      = f"{_get('gpu', 'name')} ({_get('gpu', 'performance_tier', 'unknown')} tier)"
    ram_desc      = f"{_get('ram', 'capacity', 0)}GB {_get('ram', 'type', '?')} @ {_get('ram', 'speed', 0)}MHz"
    storage_desc  = f"{_get('storage', 'capacity', 0)}GB {_get('storage', 'type', '?')}"
    psu_desc      = f"{_get('psu', 'wattage', '?')}W {_get('psu', 'efficiency_rating', '')}"
    mobo_name     = _get("motherboard", "name")
    case_name     = _get("case", "name")

    prompt = f"""You are a knowledgeable PC building expert.
Explain this build as concise bullet points — one bullet per component. Do NOT write paragraphs.

Build Summary:
- CPU: {cpu_desc}
- GPU: {gpu_desc}
- Motherboard: {mobo_name}
- RAM: {ram_desc}
- Storage: {storage_desc}
- PSU: {psu_desc}
- Case: {case_name}
- Total Cost: ₹{total_cost:,.0f}
- Remaining Budget: ₹{remaining_budget:,.0f}

Format your response EXACTLY like this — each line is a bullet starting with the component name in bold:
- **CPU**: [why this CPU was chosen — performance, value, gaming/editing fit]
- **GPU**: [why this GPU — gaming tier, FPS expectations, value]
- **Motherboard**: [why this board — compatibility, features, value]
- **RAM**: [why this RAM — capacity, speed, use case fit]
- **Storage**: [why this storage — speed, capacity, value]
- **PSU**: [why this PSU — wattage headroom, efficiency, future-proofing]
- **Case**: [why this case — airflow, GPU clearance, build quality]
- **Overall**: [one sentence on how the build fits the budget and use case, plus upgrade potential]

Keep each bullet to 1-2 sentences max. Be direct and informative.

STRICT RULE: Never mention any country name and never write currency names in words (no 'rupee', 'rupees', 'INR'). Use only the ₹ symbol for prices."""

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful and enthusiastic PC building expert."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        return sanitize_llm_text(resp.choices[0].message.content.strip())

    except Exception as e:
        print(f"[generate_explanation] LLM failed: {e}")
        cpu_name  = _get("cpu",  "name", "CPU")
        gpu_name  = _get("gpu",  "name", "GPU")
        mobo      = _get("motherboard", "name", "motherboard")
        ram_cap   = _get("ram",  "capacity", 0)
        ram_type  = _get("ram",  "type", "RAM")
        stor_cap  = _get("storage", "capacity", 0)
        stor_type = _get("storage", "type", "storage")
        psu_w     = _get("psu",  "wattage", "")
        psu_eff   = _get("psu",  "efficiency_rating", "")
        c_name    = _get("case", "name", "case")

        return sanitize_llm_text(
            f"This build features a **{cpu_name}** paired with a **{gpu_name}**, providing "
            f"strong performance for your use case. The **{mobo}** ensures solid compatibility. "
            f"**{ram_cap}GB {ram_type} RAM** keeps multitasking smooth, and the "
            f"**{stor_cap}GB {stor_type}** storage gives fast load times. "
            f"The **{psu_w}W {psu_eff}** PSU provides reliable power with headroom for future upgrades. "
            f"The **{c_name}** completes the build. "
            f"Total: ₹{total_cost:,.0f} with ₹{remaining_budget:,.0f} remaining."
        )


# ── Routes ──────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "BuildMate AI backend is running.", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "model": MODEL_NAME}


@app.get("/model")
def get_model_name():
    return {"model_name": MODEL_NAME}


@app.post("/build")
async def build_pc(request: BuildRequest):
    """
    Main endpoint — takes a user message (or full conversation history),
    extracts intent, allocates budget, validates compatibility, and returns
    a complete, explained PC build.
    """

    # ── 1. Determine latest user text ───────────────────────────────────────────
    user_text = ""
    if request.conversation:
        for msg in reversed(request.conversation):
            if msg.role == "user":
                user_text = msg.content
                break
    if not user_text and request.user_message:
        user_text = request.user_message

    if not user_text.strip():
        raise HTTPException(status_code=400, detail="No user message provided.")

    # ── 1.5. Check if user is asking a conversational question about active build ──
    if request.current_build:
        action_intent = classify_intent(user_text, has_existing_build=True)
        if action_intent == "question":
            chat_reply = answer_build_question(user_text, request.current_build, request.conversation)
            return {
                "success": True,
                "response_type": "chat",
                "content": chat_reply,
                "input_analysis": {
                    "budget": request.budget,
                    "use_case": request.use_case,
                    "preferences": request.preferences,
                },
                "build": request.current_build.get("build") or request.current_build,
            }

    # ── 2. Extract intent (with multi-turn merging) ─────────────────────────────
    intent = extract_intent(
        user_text,
        prev_budget=request.budget,
        prev_use_case=request.use_case,
        prev_preferences=request.preferences,
    )

    if "error" in intent:
        raise HTTPException(
            status_code=422,
            detail=f"Could not understand your request: {intent['error']}",
        )

    budget      = intent.get("budget")
    use_case    = intent.get("use_case", "general")
    preferences = intent.get("preferences", {})

    if not budget or budget <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please tell me your budget (e.g., '₹80,000 for a gaming PC'). "
                "I need a budget to recommend a build."
            ),
        )

    if budget < 45000:
        raise HTTPException(
            status_code=400,
            detail=(
                "⚠️ The minimum budget to assemble a complete, fully compatible PC is ₹45,000. "
                "Please enter a price of ₹45,000 or above to build the PC."
            ),
        )

    # ── 3. Budget allocation & component selection ──────────────────────────────
    try:
        build_result = allocate_budget_and_select_components(
            float(budget), use_case, preferences
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Component database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget allocation error: {str(e)}")

    # ── 4. Compatibility validation ─────────────────────────────────────────────
    selected = build_result.get("selected_components", {})
    compat_errors: List[str] = []

    cpu         = selected.get("cpu")
    motherboard = selected.get("motherboard")
    ram         = selected.get("ram")
    gpu         = selected.get("gpu")
    psu         = selected.get("psu")
    case        = selected.get("case")

    if cpu and motherboard:
        if not check_cpu_motherboard_compatibility(cpu, motherboard):
            compat_errors.append("CPU socket does not match motherboard socket")

    if ram and motherboard:
        if not check_ram_type_compatibility(ram, motherboard):
            compat_errors.append("RAM type not supported by motherboard")

    if psu and (cpu or gpu):
        psu_check = {}
        if cpu: psu_check["cpu"] = cpu
        if gpu: psu_check["gpu"] = gpu
        if not check_psu_wattage_sufficiency(psu_check, psu):
            compat_errors.append("PSU wattage insufficient (need 30% headroom over total TDP)")

    if gpu and case:
        if not check_gpu_case_compatibility(gpu, case):
            compat_errors.append("GPU length exceeds case clearance")

    compatibility_passed = len(compat_errors) == 0

    # ── 5. Analytics (Power, Bottleneck, Alternatives, Retailer Links) ──────────
    power_analysis = calculate_power_analysis(selected)
    bottleneck_analysis = calculate_bottleneck_analysis(selected, use_case)
    alternatives = find_cost_saving_alternatives(selected, float(budget))
    retailer_links = generate_retailer_links(selected)

    # ── 6. Generate explanation ─────────────────────────────────────────────────
    explanation = generate_explanation(build_result)

    # ── 7. Return response ──────────────────────────────────────────────────────
    return {
        "success": True,
        "response_type":        "build",
        "input_analysis": {
            "budget":      budget,
            "use_case":    use_case,
            "preferences": preferences,
        },
        "build":                build_result,
        "power_analysis":       power_analysis,
        "bottleneck_analysis":  bottleneck_analysis,
        "alternatives":         alternatives,
        "retailer_links":       retailer_links,
        "explanation":          explanation,
        "warnings":             compat_errors if compat_errors else None,
        "compatibility_passed": compatibility_passed,
    }


# ── Global exception handler ────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — returns a clean JSON error instead of a raw 500 traceback."""
    # Don't swallow HTTPExceptions — let FastAPI handle them normally
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    print(f"[global_exception_handler] Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )