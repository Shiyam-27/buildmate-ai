import json
import os
from typing import Dict, List, Any, Tuple

# Resolve the data directory relative to THIS file — not the process CWD.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def load_json(filename: str) -> List[Dict[str, Any]]:
    """Load JSON data from the data directory (path always resolved relative to this file)."""
    filepath = os.path.join(_DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def check_cpu_motherboard_compatibility(cpu: Dict, motherboard: Dict) -> bool:
    """
    Check if CPU socket matches motherboard socket.

    Returns:
        True if compatible, False otherwise
    """
    return cpu.get("socket") == motherboard.get("socket")


def check_ram_type_compatibility(ram: Dict, motherboard: Dict) -> bool:
    """
    Check if RAM type matches motherboard support (DDR4 / DDR5).

    Returns:
        True if compatible, False otherwise
    """
    return ram.get("type") == motherboard.get("ram_type")


def calculate_total_tdp(components: Dict[str, Dict]) -> float:
    """
    Calculate total TDP of the system (CPU + GPU).

    Args:
        components: Dictionary containing 'cpu' and optionally 'gpu' components

    Returns:
        Total TDP in watts
    """
    total = 0.0
    if "cpu" in components and components["cpu"]:
        total += components["cpu"].get("tdp", 0)
    if "gpu" in components and components["gpu"]:
        total += components["gpu"].get("tdp", 0)
    return total


def check_psu_wattage_sufficiency(components: Dict[str, Dict], psu: Dict) -> bool:
    """
    Check if PSU wattage is sufficient with 30% headroom over total TDP.

    Returns:
        True if psu.wattage >= (total_tdp * 1.3), False otherwise
    """
    required = calculate_total_tdp(components) * 1.3
    return psu.get("wattage", 0) >= required


def check_gpu_case_compatibility(gpu: Dict, case: Dict) -> bool:
    """
    Check if GPU length fits within case clearance.

    Returns:
        True if gpu.length_mm <= case.max_gpu_length_mm, False otherwise
    """
    return gpu.get("length_mm", 0) <= case.get("max_gpu_length_mm", 0)


def validate_build_compatibility(build: Dict[str, Dict]) -> List[str]:
    """
    Validate compatibility of a complete build.

    Args:
        build: Dictionary with keys 'cpu', 'motherboard', 'ram', 'gpu', 'psu', 'case'

    Returns:
        List of compatibility error messages (empty list = fully compatible)
    """
    errors: List[str] = []

    required = ["cpu", "motherboard", "ram", "gpu", "psu", "case"]
    for comp in required:
        if not build.get(comp):
            errors.append(f"Missing component: {comp}")

    cpu         = build.get("cpu")
    motherboard = build.get("motherboard")
    ram         = build.get("ram")
    gpu         = build.get("gpu")
    psu         = build.get("psu")
    case        = build.get("case")

    if cpu and motherboard:
        if not check_cpu_motherboard_compatibility(cpu, motherboard):
            errors.append("CPU socket does not match motherboard socket")

    if ram and motherboard:
        if not check_ram_type_compatibility(ram, motherboard):
            errors.append("RAM type not supported by motherboard")

    if psu:
        components_for_psu: Dict[str, Dict] = {}
        if cpu:
            components_for_psu["cpu"] = cpu
        if gpu:
            components_for_psu["gpu"] = gpu
        if components_for_psu:
            if not check_psu_wattage_sufficiency(components_for_psu, psu):
                errors.append("PSU wattage insufficient (need 30% headroom over total TDP)")

    if gpu and case:
        if not check_gpu_case_compatibility(gpu, case):
            errors.append("GPU length exceeds case clearance")

    return errors


# ── Unit tests (run with: python engine/compatibility.py) ─────────────────────
def test_load_json():
    cpus = load_json("cpus.json")
    assert len(cpus) > 0
    assert "socket"     in cpus[0]
    assert "tdp"        in cpus[0]
    assert "core_count" in cpus[0]
    print("  test_load_json: PASS")

def test_cpu_motherboard_compatibility():
    cpus         = load_json("cpus.json")
    motherboards = load_json("motherboards.json")

    am4_cpu = next((c for c in cpus if c.get("socket") == "AM4"), None)
    am4_mb  = next((m for m in motherboards if m.get("socket") == "AM4"), None)
    lga_mb  = next((m for m in motherboards if m.get("socket") == "LGA1700"), None)

    assert am4_cpu is not None and am4_mb is not None and lga_mb is not None
    assert check_cpu_motherboard_compatibility(am4_cpu, am4_mb)  == True
    assert check_cpu_motherboard_compatibility(am4_cpu, lga_mb)  == False
    print("  test_cpu_motherboard_compatibility: PASS")

def test_ram_type_compatibility():
    rams         = load_json("ram.json")
    motherboards = load_json("motherboards.json")

    ddr4_ram = next((r for r in rams if r.get("type") == "DDR4"), None)
    ddr5_ram = next((r for r in rams if r.get("type") == "DDR5"), None)
    ddr4_mb  = next((m for m in motherboards if m.get("ram_type") == "DDR4"), None)

    assert ddr4_ram is not None and ddr5_ram is not None and ddr4_mb is not None
    assert check_ram_type_compatibility(ddr4_ram, ddr4_mb) == True
    assert check_ram_type_compatibility(ddr5_ram, ddr4_mb) == False
    print("  test_ram_type_compatibility: PASS")

def test_psu_wattage_sufficiency():
    # 65W CPU + 150W GPU = 215W → need 279.5W
    comps = {"cpu": {"tdp": 65}, "gpu": {"tdp": 150}}
    assert check_psu_wattage_sufficiency(comps, {"wattage": 300}) == True
    assert check_psu_wattage_sufficiency(comps, {"wattage": 250}) == False
    # No GPU: 65W → need 84.5W
    assert check_psu_wattage_sufficiency({"cpu": {"tdp": 65}}, {"wattage": 100}) == True
    print("  test_psu_wattage_sufficiency: PASS")

def test_gpu_case_compatibility():
    gpus  = load_json("gpus.json")
    cases = load_json("cases.json")

    gtx_1660s = next((g for g in gpus if "GTX 1660 Super" in g.get("name", "")), None)
    roomy     = next((c for c in cases if c.get("max_gpu_length_mm", 0) >= 420), None)

    assert gtx_1660s is not None and roomy is not None
    assert check_gpu_case_compatibility(gtx_1660s, roomy) == True
    print("  test_gpu_case_compatibility: PASS")

if __name__ == "__main__":
    print("Running compatibility.py unit tests...")
    test_load_json()
    test_cpu_motherboard_compatibility()
    test_ram_type_compatibility()
    test_psu_wattage_sufficiency()
    test_gpu_case_compatibility()
    print("All tests passed!")