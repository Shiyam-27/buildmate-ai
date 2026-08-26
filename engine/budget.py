import json
import os
from typing import Dict, List, Any, Tuple, Optional

# Resolve the data directory relative to THIS file, not the CWD.
# This ensures load_json works no matter where uvicorn / the process is launched from.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

def load_json(filename: str) -> List[Dict[str, Any]]:
    """Load JSON data from the data directory (path is always resolved relative to this file)."""
    filepath = os.path.join(_DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_minimum_component_costs() -> Dict[str, float]:
    """
    Get the minimum cost for each component category.

    Returns:
        Dictionary mapping component categories to their minimum cost
    """
    try:
        cpus        = load_json("cpus.json")
        gpus        = load_json("gpus.json")
        motherboards = load_json("motherboards.json")
        rams        = load_json("ram.json")
        psus        = load_json("psus.json")
        cases       = load_json("cases.json")
        storages    = load_json("storage.json")

        return {
            "cpu":         min(cpu.get("price",    float("inf")) for cpu in cpus),
            "gpu":         min(gpu.get("price",    float("inf")) for gpu in gpus),
            "motherboard": min(mb.get("price",     float("inf")) for mb in motherboards),
            "ram":         min(ram.get("price",    float("inf")) for ram in rams),
            "psu":         min(psu.get("price",    float("inf")) for psu in psus),
            "case":        min(case.get("price",   float("inf")) for case in cases),
            "storage":     min(storage.get("price", float("inf")) for storage in storages),
        }
    except (ValueError, FileNotFoundError):
        # Fallback values if files are empty or missing
        return {
            "cpu":         129.0,
            "gpu":         229.0,
            "motherboard":  59.0,
            "ram":          25.0,
            "psu":          45.0,
            "case":         59.0,
            "storage":      22.0,
        }


def get_budget_allocation_priorities(use_case: str) -> Dict[str, float]:
    """
    Get budget allocation priorities for each component category based on use case.
    These are weights for distributing excess budget after minimums are met.

    Args:
        use_case: One of 'gaming', 'editing', or 'general'

    Returns:
        Dictionary mapping component categories to priority weights (higher = more priority)
    """
    base_priorities = {
        "cpu":         1.0,
        "gpu":         1.0,
        "motherboard": 0.5,
        "ram":         1.0,
        "storage":     0.5,
        "psu":         0.5,
        "case":        0.3,
    }

    if use_case.lower() == "gaming":
        return {
            "cpu":         1.5,
            "gpu":         3.0,   # Highest priority for gaming
            "motherboard": 0.5,
            "ram":         1.0,
            "storage":     0.5,
            "psu":         0.5,
            "case":        0.3,
        }
    elif use_case.lower() == "editing":
        return {
            "cpu":         2.5,   # High CPU priority for editing
            "gpu":         1.0,
            "motherboard": 0.5,
            "ram":         2.0,   # High RAM priority for editing
            "storage":     1.5,   # More storage for large files
            "psu":         0.5,
            "case":        0.3,
        }
    else:
        return base_priorities


def filter_components_by_budget(
    components: List[Dict[str, Any]],
    max_price: float,
    fallback_cheapest: bool = True,
) -> List[Dict[str, Any]]:
    """Filter components to those within budget. If none fit and fallback_cheapest is True, return the cheapest available option as fallback."""
    if not components:
        return []
    filtered = [c for c in components if c.get("price", float("inf")) <= max_price]
    if not filtered and fallback_cheapest:
        cheapest = min(components, key=lambda c: c.get("price", float("inf")))
        return [cheapest]
    return filtered


def select_best_component(components: List[Dict[str, Any]], score_func) -> Optional[Dict[str, Any]]:
    """
    Select the best component from a list based on a scoring function.

    Args:
        components: List of component dictionaries
        score_func: Function that takes a component and returns a score (higher is better)

    Returns:
        Best component or None if list is empty
    """
    if not components:
        return None
    try:
        scored = [(c, score_func(c)) for c in components]
        valid  = [(c, s) for c, s in scored if s is not None]
        if not valid:
            return components[0]
        return max(valid, key=lambda x: x[1])[0]
    except Exception:
        return components[0] if components else None


def allocate_budget_and_select_components(
    total_budget: float,
    use_case: str,
    preferences: dict = None,
) -> Dict[str, Any]:
    """
    Allocate budget across component categories and select best-fit components.

    Algorithm:
    1. Calculate minimum required cost for each component (cheapest available)
    2. If total_budget < sum of minimums, allocate proportionally to minimums
    3. Otherwise:
       - Allocate minimum cost to each category
       - Distribute remaining budget according to use-case priorities
    4. Select best component for each category within its allocated budget

    Args:
        total_budget: Total budget in INR
        use_case: Use case ('gaming', 'editing', or 'general')
        preferences: Dictionary of user preferences (e.g., {'cpu_brand': 'AMD'})

    Returns:
        Dictionary with selected components and remaining budget
    """
    if preferences is None:
        preferences = {}

    # Load component data (paths are absolute — safe from any CWD)
    try:
        cpus        = load_json("cpus.json")
        gpus        = load_json("gpus.json")
        motherboards = load_json("motherboards.json")
        rams        = load_json("ram.json")
        storages    = load_json("storage.json")
        psus        = load_json("psus.json")
        cases       = load_json("cases.json")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Component data file not found: {e.filename}")

    notes = []

    # ── Step 1: initial minimum costs ──────────────────────────────────────────
    min_costs = get_minimum_component_costs()
    total_min_cost = sum(min_costs.values())

    def _compute_category_budgets(min_c: Dict[str, float]) -> Dict[str, float]:
        total_min = sum(min_c.values())
        if total_budget < total_min:
            return {cat: (v / total_min) * total_budget for cat, v in min_c.items()}
        budgets = min_c.copy()
        remaining = total_budget - total_min
        priorities = get_budget_allocation_priorities(use_case)
        total_prio = sum(priorities.values())
        if total_prio > 0:
            for cat, prio in priorities.items():
                budgets[cat] += (prio / total_prio) * remaining
        return budgets

    category_budgets = _compute_category_budgets(min_costs)

    # ── Step 2: Select CPU ─────────────────────────────────────────────────────
    cpu_budget = category_budgets["cpu"]
    cpu_brand_pref = preferences.get("cpu_brand")
    cpu_model_pref = preferences.get("cpu_model")

    if cpu_model_pref:
        model_cpus = [c for c in cpus if cpu_model_pref.lower() in c.get("name", "").lower()]
        if model_cpus:
            selected_cpu = model_cpus[0]
            notes.append(f"Using requested CPU model '{selected_cpu.get('name')}'.")
        else:
            affordable_cpus = filter_components_by_budget(cpus, cpu_budget)
            selected_cpu = select_best_component(affordable_cpus, lambda c: c.get("core_count", 0))
    elif cpu_brand_pref:
        brand_cpus = [c for c in cpus if cpu_brand_pref.lower() in c.get("name", "").lower()]
        affordable_brand = filter_components_by_budget(brand_cpus, cpu_budget)
        if affordable_brand:
            affordable_cpus = affordable_brand
            notes.append(f"Using preferred CPU brand '{cpu_brand_pref}'.")
        else:
            affordable_cpus = filter_components_by_budget(cpus, cpu_budget)
            notes.append(
                f"No CPUs matching brand '{cpu_brand_pref}' within budget ₹{cpu_budget:.0f}; "
                "falling back to best available."
            )
        selected_cpu = select_best_component(affordable_cpus, lambda c: c.get("core_count", 0))
    else:
        affordable_cpus = filter_components_by_budget(cpus, cpu_budget)
        selected_cpu = select_best_component(affordable_cpus, lambda c: c.get("core_count", 0))

    # ── Step 3: Recompute motherboard minimum using CPU socket ─────────────────
    adjusted_min_costs = min_costs.copy()
    if selected_cpu and isinstance(selected_cpu, dict):
        cpu_socket = selected_cpu.get("socket")
        if cpu_socket:
            socket_mbs = [mb for mb in motherboards if mb.get("socket") == cpu_socket]
            if socket_mbs:
                adjusted_min_costs["motherboard"] = min(
                    mb.get("price", float("inf")) for mb in socket_mbs
                )

    category_budgets = _compute_category_budgets(adjusted_min_costs)

    # Re-check CPU still fits in updated budget if not a forced model
    if not cpu_model_pref:
        cpu_budget = category_budgets["cpu"]
        if selected_cpu and selected_cpu.get("price", 0) > cpu_budget:
            if cpu_brand_pref:
                brand_cpus = [c for c in cpus if cpu_brand_pref.lower() in c.get("name", "").lower()]
                affordable_brand = filter_components_by_budget(brand_cpus, cpu_budget)
                affordable_cpus = affordable_brand if affordable_brand else filter_components_by_budget(cpus, cpu_budget)
            else:
                affordable_cpus = filter_components_by_budget(cpus, cpu_budget)
            selected_cpu = select_best_component(affordable_cpus, lambda c: c.get("core_count", 0))

    selected_components: Dict[str, Any] = {"cpu": selected_cpu}

    # ── Step 4: Select Motherboard ─────────────────────────────────────────────
    mb_budget = category_budgets["motherboard"]
    candidate_mbs = motherboards
    if selected_cpu and isinstance(selected_cpu, dict):
        cpu_socket = selected_cpu.get("socket")
        if cpu_socket:
            socket_mbs = [mb for mb in motherboards if mb.get("socket") == cpu_socket]
            if socket_mbs:
                candidate_mbs = socket_mbs
            else:
                notes.append(
                    f"CPU socket '{cpu_socket}' has no compatible motherboards; "
                    "falling back to any motherboard."
                )

    affordable_mbs = filter_components_by_budget(candidate_mbs, mb_budget)
    selected_motherboard = select_best_component(
        affordable_mbs, lambda mb: mb.get("price", 0)  # higher price = better features
    )
    selected_components["motherboard"] = selected_motherboard

    # ── Step 5: Select GPU ─────────────────────────────────────────────────────
    gpu_budget = category_budgets["gpu"]
    gpu_brand_pref = preferences.get("gpu_brand")
    gpu_model_pref = preferences.get("gpu_model")

    def gpu_score(g):
        tier_values = {"budget": 1, "mid-range": 2, "high-end": 3, "enthusiast": 4}
        return tier_values.get(g.get("performance_tier", "budget"), 0) * 100 + g.get("tdp", 0)

    if gpu_model_pref:
        model_gpus = [g for g in gpus if gpu_model_pref.lower() in g.get("name", "").lower()]
        if model_gpus:
            selected_components["gpu"] = model_gpus[0]
            notes.append(f"Using requested GPU model '{model_gpus[0].get('name')}'.")
        else:
            affordable_gpus = filter_components_by_budget(gpus, gpu_budget)
            selected_components["gpu"] = select_best_component(affordable_gpus, gpu_score)
    elif gpu_brand_pref:
        brand_gpus = [g for g in gpus if gpu_brand_pref.lower() in g.get("name", "").lower()]
        affordable_brand_gpus = filter_components_by_budget(brand_gpus, gpu_budget)
        if affordable_brand_gpus:
            affordable_gpus = affordable_brand_gpus
            notes.append(f"Using preferred GPU brand '{gpu_brand_pref}'.")
        else:
            affordable_gpus = filter_components_by_budget(gpus, gpu_budget)
            notes.append(
                f"No GPUs matching brand '{gpu_brand_pref}' within budget ₹{gpu_budget:.0f}; "
                "falling back to best available."
            )
        selected_components["gpu"] = select_best_component(affordable_gpus, gpu_score)
    else:
        affordable_gpus = filter_components_by_budget(gpus, gpu_budget)
        selected_components["gpu"] = select_best_component(affordable_gpus, gpu_score)

    # ── Step 6: Select RAM ─────────────────────────────────────────────────────
    ram_budget = category_budgets["ram"]
    preferred_ram_type = preferences.get("ram_type") or preferences.get("ram")
    filtered_rams = rams

    # Filter by user's RAM type preference first
    if preferred_ram_type:
        pref_rams = [r for r in rams if r.get("type") == preferred_ram_type]
        filtered_rams = pref_rams if pref_rams else rams

    # Then further filter by motherboard's supported RAM type (hard constraint)
    if selected_motherboard and isinstance(selected_motherboard, dict):
        mobo_ram_type = selected_motherboard.get("ram_type")
        if mobo_ram_type:
            mobo_compat = [r for r in filtered_rams if r.get("type") == mobo_ram_type]
            if mobo_compat:
                filtered_rams = mobo_compat

    affordable_rams = filter_components_by_budget(filtered_rams, ram_budget)
    selected_components["ram"] = select_best_component(
        affordable_rams,
        lambda r: r.get("capacity", 0) * r.get("speed", 0),
    )

    # ── Step 7: Select Storage ─────────────────────────────────────────────────
    storage_budget = category_budgets["storage"]
    affordable_storages = filter_components_by_budget(storages, storage_budget)

    def storage_score(s):
        type_bonus      = 1000 if s.get("type") == "NVMe" else 0
        interface_bonus = {"PCIe 4.0 x4": 500, "PCIe 3.0 x4": 250, "SATA": 0}.get(
            s.get("interface", ""), 0
        )
        return type_bonus + s.get("capacity", 0) + interface_bonus

    selected_components["storage"] = select_best_component(affordable_storages, storage_score)

    # ── Step 8: Select PSU ─────────────────────────────────────────────────────
    psu_budget = category_budgets["psu"]
    affordable_psus = filter_components_by_budget(psus, psu_budget)

    def psu_score(p):
        eff_bonus = {
            "80+ White":    0,
            "80+ Bronze":   50,
            "80+ Silver":   100,
            "80+ Gold":     150,
            "80+ Platinum": 200,
            "80+ Titanium": 250,
        }.get(p.get("efficiency_rating", ""), 0)
        modular_bonus = {
            "Full-Modular": 100,
            "Semi-Modular":  50,
            "Non-Modular":    0,
        }.get(p.get("modular", ""), 0)
        return p.get("wattage", 0) + eff_bonus + modular_bonus

    selected_components["psu"] = select_best_component(affordable_psus, psu_score)

    # ── Step 9: Select Case ────────────────────────────────────────────────────
    case_budget = category_budgets["case"]
    affordable_cases = filter_components_by_budget(cases, case_budget)

    def case_score(c):
        features = 0
        if c.get("tempered_glass"): features += 50
        if c.get("airflow") == "high": features += 50
        if c.get("rgb"):            features += 25
        if c.get("sfx"):            features += 25
        return c.get("max_gpu_length_mm", 0) + features

    selected_components["case"] = select_best_component(affordable_cases, case_score)

    # ── Totals ─────────────────────────────────────────────────────────────────
    total_cost = sum(
        comp.get("price", 0)
        for comp in selected_components.values()
        if comp is not None
    )
    remaining_budget = total_budget - total_cost

    return {
        "selected_components": selected_components,
        "total_cost":          total_cost,
        "remaining_budget":    remaining_budget,
        "min_costs":           min_costs,
        "category_budgets":    category_budgets,
        "notes":               notes,
    }


# ── Unit tests (run with: python engine/budget.py) ────────────────────────────
def test_load_json():
    cpus = load_json("cpus.json")
    assert len(cpus) > 0
    assert "socket"     in cpus[0]
    assert "tdp"        in cpus[0]
    assert "core_count" in cpus[0]
    print("  test_load_json: PASS")

def test_get_minimum_component_costs():
    min_costs = get_minimum_component_costs()
    for cat in ["cpu", "gpu", "motherboard", "ram", "psu", "case", "storage"]:
        assert cat in min_costs
        assert min_costs[cat] > 0
    print("  test_get_minimum_component_costs: PASS")

def test_get_budget_allocation_priorities():
    general = get_budget_allocation_priorities("general")
    gaming  = get_budget_allocation_priorities("gaming")
    editing = get_budget_allocation_priorities("editing")
    assert gaming["gpu"]   > general["gpu"]
    assert editing["cpu"]  > general["cpu"]
    assert editing["ram"]  > general["ram"]
    print("  test_get_budget_allocation_priorities: PASS")

def test_filter_components_by_budget():
    cpus = load_json("cpus.json")
    low  = filter_components_by_budget(cpus, 5000.0, fallback_cheapest=False)
    high = filter_components_by_budget(cpus, 200000.0)
    assert low == []
    assert len(high) > 0
    # Test fallback
    fb = filter_components_by_budget(cpus, 5000.0, fallback_cheapest=True)
    assert len(fb) == 1
    print("  test_filter_components_by_budget: PASS")

def test_select_best_component():
    cpus = load_json("cpus.json")
    affordable = filter_components_by_budget(cpus, 50000.0)
    if affordable:
        best = select_best_component(affordable, lambda c: c.get("core_count", 0))
        assert best is not None
        max_cores = max(c.get("core_count", 0) for c in affordable)
        assert best.get("core_count", 0) == max_cores
    print("  test_select_best_component: PASS")

def test_allocate_budget_and_select_components():
    result = allocate_budget_and_select_components(100000.0, "gaming")
    assert "selected_components" in result
    assert "total_cost" in result
    assert "remaining_budget" in result
    assert result["total_cost"] >= 0
    assert result["remaining_budget"] >= 0
    for cat in ["cpu", "gpu", "motherboard", "ram", "storage", "psu", "case"]:
        assert cat in result["selected_components"]
    # Test all use cases
    for uc in ["gaming", "editing", "general"]:
        r = allocate_budget_and_select_components(150000.0, uc)
        assert isinstance(r, dict)
    print("  test_allocate_budget_and_select_components: PASS")

if __name__ == "__main__":
    print("Running budget.py unit tests...")
    test_load_json()
    test_get_minimum_component_costs()
    test_get_budget_allocation_priorities()
    test_filter_components_by_budget()
    test_select_best_component()
    test_allocate_budget_and_select_components()
    print("All tests passed!")