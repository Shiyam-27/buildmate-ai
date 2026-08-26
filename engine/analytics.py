import urllib.parse
import os
import json
from typing import Dict, List, Any, Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

def load_json(filename: str) -> List[Dict[str, Any]]:
    filepath = os.path.join(_DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_power_analysis(selected_components: Dict[str, Any]) -> Dict[str, Any]:
    cpu = selected_components.get("cpu") or {}
    gpu = selected_components.get("gpu") or {}
    psu = selected_components.get("psu") or {}

    cpu_tdp = float(cpu.get("tdp", 65))
    gpu_tdp = float(gpu.get("tdp", 0)) if gpu else 0.0
    base_overhead = 50.0

    peak_power = cpu_tdp + gpu_tdp + base_overhead
    recommended_psu_wattage = int(round((peak_power * 1.3) / 50.0) * 50)

    psu_wattage = float(psu.get("wattage", 550))
    psu_efficiency = psu.get("efficiency_rating", "80+ Bronze")

    utilization_pct = round((peak_power / psu_wattage) * 100, 1) if psu_wattage > 0 else 0

    if utilization_pct < 45:
        load_status = "Light Load (Very quiet & cool)"
    elif utilization_pct <= 75:
        load_status = "Optimal Load (Maximum efficiency & longevity)"
    elif utilization_pct <= 85:
        load_status = "Moderate High Load (Acceptable)"
    else:
        load_status = "Heavy Load (Consider higher wattage PSU)"

    active_watts = peak_power * 0.80
    idle_watts = 55.0

    daily_kwh = ((active_watts * 4.0) + (idle_watts * 4.0)) / 1000.0
    monthly_kwh = daily_kwh * 30.0
    yearly_kwh = daily_kwh * 365.0

    electricity_rate_inr = 8.0  # ₹8 per unit (kWh)
    monthly_cost_inr = round(monthly_kwh * electricity_rate_inr, 0)
    yearly_cost_inr = round(yearly_kwh * electricity_rate_inr, 0)

    return {
        "cpu_tdp": int(cpu_tdp),
        "gpu_tdp": int(gpu_tdp),
        "base_overhead": int(base_overhead),
        "peak_power_watts": int(round(peak_power)),
        "recommended_psu_watts": recommended_psu_wattage,
        "selected_psu_watts": int(psu_wattage),
        "psu_efficiency": psu_efficiency,
        "psu_load_percentage": utilization_pct,
        "load_status": load_status,
        "daily_kwh": round(daily_kwh, 2),
        "monthly_kwh": round(monthly_kwh, 1),
        "monthly_cost_inr": int(monthly_cost_inr),
        "yearly_cost_inr": int(yearly_cost_inr),
        "tariff_rate": electricity_rate_inr,
    }


def calculate_bottleneck_analysis(
    selected_components: Dict[str, Any], use_case: str = "gaming"
) -> Dict[str, Any]:
    cpu = selected_components.get("cpu") or {}
    gpu = selected_components.get("gpu") or {}

    cpu_name = cpu.get("name", "Unknown CPU")
    cpu_cores = int(cpu.get("core_count", 6))
    gpu_name = gpu.get("name", "Integrated Graphics")
    gpu_tier = gpu.get("performance_tier", "budget")

    cpu_tier_score = 1.0
    if cpu_cores >= 16:
        cpu_tier_score = 4.5
    elif cpu_cores >= 12:
        cpu_tier_score = 4.0
    elif cpu_cores >= 8:
        cpu_tier_score = 3.5
    elif cpu_cores >= 6:
        cpu_tier_score = 2.5
    else:
        cpu_tier_score = 1.5

    if any(flag in cpu_name for flag in ["X3D", "i7-13", "i7-14", "i9-13", "i9-14", "7800X3D", "7950X"]):
        cpu_tier_score += 0.5

    tier_map = {"budget": 1.5, "mid-range": 2.5, "high-end": 3.8, "enthusiast": 4.8}
    gpu_tier_score = tier_map.get(gpu_tier.lower(), 2.0)

    score_diff = cpu_tier_score - gpu_tier_score

    if abs(score_diff) <= 0.6:
        bottleneck_pct = round(abs(score_diff) * 5 + 3, 1)
        bottleneck_type = "Balanced"
        status_label = "Optimal Match (Bottleneck < 8%)"
        status_color = "green"
        explanation = (
            f"The **{cpu_name}** and **{gpu_name}** are well-matched. "
            "Neither component significantly holds back the other in real-world workloads."
        )
    elif score_diff > 0.6:
        bottleneck_pct = round(min(30.0, score_diff * 10), 1)
        bottleneck_type = "GPU Bound"
        status_label = "GPU-Bound (Great for high-res gaming)"
        status_color = "blue"
        explanation = (
            f"The **{cpu_name}** has plenty of processing headroom for the **{gpu_name}**. "
            "Your GPU will operate at 100% capacity with zero CPU frame stuttering."
        )
    else:
        bottleneck_pct = round(min(35.0, abs(score_diff) * 12), 1)
        bottleneck_type = "CPU Bottleneck"
        status_label = f"CPU Bottleneck (~{bottleneck_pct:.0f}% at 1080p)"
        status_color = "amber"
        explanation = (
            f"The **{gpu_name}** is very powerful relative to the **{cpu_name}**. "
            "At 1080p competitive settings, the CPU may limit peak frame rates, "
            "but at 1440p or 4K the GPU will carry the heavy load smoothly."
        )

    resolutions = {
        "1080p_fhd": {
            "label": "1080p (Full HD)",
            "assessment": "CPU-dependent" if bottleneck_type == "CPU Bottleneck" else "Smooth high FPS",
            "rating": "Good" if bottleneck_type != "CPU Bottleneck" else "Moderate",
        },
        "1440p_qhd": {
            "label": "1440p (Quad HD / 2K)",
            "assessment": "Sweet spot balance — optimal GPU utilization",
            "rating": "Excellent",
        },
        "4k_uhd": {
            "label": "4K (Ultra HD)",
            "assessment": "100% GPU-bound — CPU bottleneck negligible",
            "rating": "GPU Limited" if gpu_tier in ["budget", "mid-range"] else "Excellent",
        },
    }

    return {
        "bottleneck_type": bottleneck_type,
        "bottleneck_percentage": bottleneck_pct,
        "status_label": status_label,
        "status_color": status_color,
        "explanation": explanation,
        "cpu_tier_score": round(cpu_tier_score, 1),
        "gpu_tier_score": round(gpu_tier_score, 1),
        "resolutions": resolutions,
    }


def find_cost_saving_alternatives(
    selected_components: Dict[str, Any], total_budget: float
) -> List[Dict[str, Any]]:
    alternatives = []

    try:
        cpus = load_json("cpus.json")
        motherboards = load_json("motherboards.json")
        gpus = load_json("gpus.json")
        rams = load_json("ram.json")
    except Exception:
        return []

    sel_cpu = selected_components.get("cpu") or {}
    sel_mobo = selected_components.get("motherboard") or {}
    sel_gpu = selected_components.get("gpu") or {}
    sel_ram = selected_components.get("ram") or {}

    cpu_socket = sel_cpu.get("socket")
    cpu_price = sel_cpu.get("price", 0)
    if cpu_socket and cpu_price > 0:
        cheaper_cpus = [
            c for c in cpus
            if c.get("socket") == cpu_socket and c.get("price", float("inf")) < cpu_price * 0.88
        ]
        if cheaper_cpus:
            best_alt_cpu = max(cheaper_cpus, key=lambda c: c.get("price", 0))
            savings = cpu_price - best_alt_cpu.get("price", 0)
            if savings >= 1500:
                alternatives.append({
                    "category": "CPU",
                    "original": sel_cpu.get("name"),
                    "alternative": best_alt_cpu.get("name"),
                    "original_price": cpu_price,
                    "alternative_price": best_alt_cpu.get("price", 0),
                    "savings": savings,
                    "trade_off": f"{best_alt_cpu.get('core_count', '?')} cores vs {sel_cpu.get('core_count', '?')} cores — minor loss in heavy multitasking.",
                })

    mobo_price = sel_mobo.get("price", 0)
    mobo_socket = sel_mobo.get("socket")
    mobo_ram = sel_mobo.get("ram_type")
    if mobo_socket and mobo_ram and mobo_price > 0:
        cheaper_mobos = [
            m for m in motherboards
            if m.get("socket") == mobo_socket and m.get("ram_type") == mobo_ram and m.get("price", float("inf")) < mobo_price * 0.85
        ]
        if cheaper_mobos:
            best_alt_mobo = max(cheaper_mobos, key=lambda m: m.get("price", 0))
            savings = mobo_price - best_alt_mobo.get("price", 0)
            if savings >= 1000:
                alternatives.append({
                    "category": "Motherboard",
                    "original": sel_mobo.get("name"),
                    "alternative": best_alt_mobo.get("name"),
                    "original_price": mobo_price,
                    "alternative_price": best_alt_mobo.get("price", 0),
                    "savings": savings,
                    "trade_off": "Fewer PCIe slots / USB ports, but identical CPU & RAM performance.",
                })

    gpu_price = sel_gpu.get("price", 0)
    if gpu_price > 0:
        cheaper_gpus = [
            g for g in gpus
            if g.get("price", float("inf")) < gpu_price * 0.85
        ]
        if cheaper_gpus:
            best_alt_gpu = max(cheaper_gpus, key=lambda g: g.get("price", 0))
            savings = gpu_price - best_alt_gpu.get("price", 0)
            if savings >= 2500:
                alternatives.append({
                    "category": "GPU",
                    "original": sel_gpu.get("name"),
                    "alternative": best_alt_gpu.get("name"),
                    "original_price": gpu_price,
                    "alternative_price": best_alt_gpu.get("price", 0),
                    "savings": savings,
                    "trade_off": f"Step down to {best_alt_gpu.get('performance_tier', 'value')} tier (~10-15% lower FPS in ultra settings).",
                })

    return alternatives[:3]


def generate_retailer_links(selected_components: Dict[str, Any]) -> List[Dict[str, Any]]:
    links = []
    category_icons = {
        "cpu": "🖥️ CPU",
        "gpu": "🎮 GPU",
        "motherboard": "🔧 Motherboard",
        "ram": "💾 RAM",
        "storage": "💿 Storage",
        "psu": "⚡ PSU",
        "case": "📦 Case",
    }

    for cat_key, cat_label in category_icons.items():
        comp = selected_components.get(cat_key)
        if not comp or not isinstance(comp, dict):
            continue

        name = comp.get("name", "")
        if not name:
            if cat_key == "ram":
                name = f"{comp.get('capacity', 16)}GB {comp.get('type', 'DDR4')} {comp.get('speed', 3200)}MHz RAM"
            elif cat_key == "storage":
                name = f"{comp.get('capacity', 500)}GB {comp.get('type', 'NVMe')} SSD"
            else:
                name = cat_key.upper()

        query = urllib.parse.quote_plus(name)

        links.append({
            "category": cat_label,
            "component_name": name,
            "pcpartpicker": f"https://pcpartpicker.com/search/?q={query}",
            "amazon_in": f"https://www.amazon.in/s?k={query}",
        })

    return links
