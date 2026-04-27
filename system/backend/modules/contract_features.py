import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from pyevmasm import disassemble_all

logger = logging.getLogger("phishguard.contract_features")


def disassemble_safe(bytecode_hex: str) -> list:
    if bytecode_hex == "0x" or not bytecode_hex:
        return []
    try:
        stripped = bytecode_hex[2:]
        if len(stripped) % 2 != 0:
            stripped = "0" + stripped
        return list(disassemble_all(bytes.fromhex(stripped)))
    except Exception:
        return []


_PROXY_SLOT = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

_SLITHER_DEFAULTS = {
    "slither_warning_count_total": 0,
    "slither_low_level_call_count": 0,
    "slither_access_control_issues_count": 0,
}


def _prepare_slither_files(source_code_str: str, address: str):
    source = source_code_str.strip()
    temp_dir = tempfile.mkdtemp()
    try:
        if source.startswith("{{"):
            parsed = json.loads(source[1:-1])
            sources = parsed.get("sources", {})
            entry = None
            for filename, content in sources.items():
                filepath = os.path.join(temp_dir, os.path.basename(filename))
                with open(filepath, "w") as f:
                    f.write(content.get("content", ""))
                if entry is None:
                    entry = filepath
            return temp_dir, entry

        if source.startswith("{") and '"language"' in source:
            parsed = json.loads(source)
            sources = parsed.get("sources", {})
            entry = None
            for filename, content in sources.items():
                filepath = os.path.join(temp_dir, os.path.basename(filename))
                with open(filepath, "w") as f:
                    f.write(content.get("content", ""))
                if entry is None:
                    entry = filepath
            return temp_dir, entry

        entry = os.path.join(temp_dir, f"{address}.sol")
        with open(entry, "w") as f:
            f.write(source)
        return temp_dir, entry
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, None


def _resolve_solc_path(compiler_version_str: str) -> str:
    try:
        import solcx  # type: ignore[import-untyped]
        from packaging.version import Version as V

        ver_match = re.search(r"v?([\d]+\.[\d]+\.[\d]+)", compiler_version_str)
        target_str = ver_match.group(1) if ver_match else "0.8.19"
        home = os.path.expanduser("~")

        def binary_path(v):
            p = f"{home}/.solcx/solc-v{v}"
            return p if os.path.exists(p) else None

        if binary_path(target_str):
            return binary_path(target_str)

        try:
            solcx.install_solc(target_str, show_progress=False)
            if binary_path(target_str):
                return binary_path(target_str)
        except Exception:
            pass

        target = V(target_str)
        installed = solcx.get_installed_solc_versions()
        same_minor = [v for v in installed if v.major == target.major and v.minor == target.minor]
        if same_minor:
            best = str(max(same_minor))
            if binary_path(best):
                return binary_path(best)

        return binary_path("0.8.19")
    except Exception:
        return None


def _run_slither(entry_file: str, solc_path: str) -> dict:
    if not solc_path:
        return _SLITHER_DEFAULTS.copy()

    runner_fd, runner = tempfile.mkstemp(suffix=".py")
    os.close(runner_fd)
    output_fd, output = tempfile.mkstemp(suffix=".json")
    os.close(output_fd)
    try:
        script = f"""
import json, os, inspect
os.environ['PATH'] = os.path.dirname({repr(solc_path)}) + ':' + os.environ.get('PATH', '')
try:
    from slither.slither import Slither
    from slither.detectors.abstract_detector import AbstractDetector
    import slither.detectors.all_detectors as ad

    detector_classes = [
        cls for _, cls in inspect.getmembers(ad, inspect.isclass)
        if issubclass(cls, AbstractDetector) and cls is not AbstractDetector
    ]
    sl = Slither({repr(entry_file)}, solc={repr(solc_path)})
    for d in detector_classes:
        sl.register_detector(d)
    raw = sl.run_detectors()

    all_findings = [f for det in raw for f in det]
    total   = sum(len(f.get('elements', [])) for f in all_findings)
    low_lvl = sum(len(f.get('elements', [])) for f in all_findings
                  if 'low-level-calls' in f.get('check', ''))
    access  = sum(len(f.get('elements', [])) for f in all_findings
                  if 'access-control' in f.get('check', '')
                  or 'unprotected'    in f.get('check', ''))

    with open({repr(output)}, 'w') as fh:
        json.dump({{'total': total, 'low_lvl': low_lvl, 'access': access}}, fh)
except Exception as e:
    with open({repr(output)}, 'w') as fh:
        json.dump({{'total': 0, 'low_lvl': 0, 'access': 0, 'err': str(e)}}, fh)
"""
        with open(runner, "w") as f:
            f.write(script)

        subprocess.run(["python3", runner], timeout=30, capture_output=True)

        if os.path.exists(output):
            with open(output) as f:
                data = json.load(f)
            return {
                "slither_warning_count_total":         data.get("total",   0),
                "slither_low_level_call_count":        data.get("low_lvl", 0),
                "slither_access_control_issues_count": data.get("access",  0),
            }
        return _SLITHER_DEFAULTS.copy()
    except subprocess.TimeoutExpired:
        logger.warning(f"Slither timed out on {entry_file}")
        return _SLITHER_DEFAULTS.copy()
    except Exception as exc:
        logger.warning(f"Slither failed: {exc}")
        return _SLITHER_DEFAULTS.copy()
    finally:
        for f in [runner, output]:
            try:
                os.unlink(f)
            except Exception:
                pass


def _get_slither_features(source_code: str, compiler_version: str, address: str) -> dict:
    if not source_code or not source_code.strip():
        return _SLITHER_DEFAULTS.copy()
    try:
        solc_path = _resolve_solc_path(compiler_version)
        if not solc_path:
            logger.warning(f"No solc binary found for {compiler_version}, skipping Slither")
            return _SLITHER_DEFAULTS.copy()

        temp_dir, entry_file = _prepare_slither_files(source_code, address)
        if entry_file is None:
            return _SLITHER_DEFAULTS.copy()

        result = _run_slither(entry_file, solc_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return result
    except Exception as exc:
        logger.warning(f"Slither pipeline failed for {address}: {exc}")
        return _SLITHER_DEFAULTS.copy()


def compute_contract_features(raw_data: dict) -> dict:
    bytecode_hex: str = raw_data.get("bytecode_hex", "0x") or "0x"
    abi_list: list = raw_data.get("abi_list", []) or []
    is_verified: int = int(raw_data.get("is_verified", 0))
    source_code: str = raw_data.get("source_code", "") or ""
    compiler_version: str = raw_data.get("compiler_version", "") or ""
    address: str = raw_data.get("address", "unknown")

    # ── Bytecode size ─────────────────────────────────────────────────────────
    bytecode_size = (len(bytecode_hex) - 2) // 2 if bytecode_hex != "0x" else 0

    # ── Disassemble ───────────────────────────────────────────────────────────
    instructions = disassemble_safe(bytecode_hex)
    total_instructions = len(instructions)

    # Opcode name → count / pc list
    opcode_counts: dict = {}
    call_pcs: list = []
    for insn in instructions:
        name = insn.name
        opcode_counts[name] = opcode_counts.get(name, 0) + 1
        if name == "CALL":
            call_pcs.append(insn.pc)

    def opcode_freq(name: str) -> float:
        if total_instructions == 0:
            return 0.0
        return opcode_counts.get(name, 0) / total_instructions

    # ── ABI features ──────────────────────────────────────────────────────────
    abi_function_count = sum(1 for item in abi_list if item.get("type") == "function")

    external_public_function_count = 0
    approval_related_function_flag = 0
    permit_related_function_flag = 0
    setApprovalForAll_flag = 0

    _APPROVAL_NAMES = {"approve", "setallowance", "increaseallowance", "decreaseallowance"}

    for item in abi_list:
        if item.get("type") != "function":
            continue

        # Determine if state-changing (external/public non-view/pure)
        state_mut = item.get("stateMutability", None)
        if state_mut is not None:
            is_view = state_mut in ("view", "pure")
        else:
            # Old ABI format: constant==True means view
            is_view = bool(item.get("constant", False))

        if not is_view:
            external_public_function_count += 1

        name_lower = item.get("name", "").lower()
        if any(n in name_lower for n in _APPROVAL_NAMES):
            approval_related_function_flag = 1
        if "permit" in name_lower:
            permit_related_function_flag = 1
        if name_lower == "setapprovalforall":
            setApprovalForAll_flag = 1

    # ── Opcode frequencies ────────────────────────────────────────────────────
    freq_CALL = opcode_freq("CALL")
    freq_DELEGATECALL = opcode_freq("DELEGATECALL")
    freq_SELFDESTRUCT = opcode_freq("SELFDESTRUCT")
    freq_SSTORE = opcode_freq("SSTORE")
    freq_JUMPI = opcode_freq("JUMPI")

    external_call_sites_count = len(set(call_pcs))
    has_create2 = 1 if "CREATE2" in opcode_counts else 0

    # ── Proxy pattern ─────────────────────────────────────────────────────────
    proxy_pattern_detected = 1 if _PROXY_SLOT in bytecode_hex.lower() else 0

    # ── Sliding window patterns (window=10) ───────────────────────────────────
    approval_then_external_call_pattern = 0
    approval_then_state_mutation_pattern = 0
    if total_instructions >= 10:
        opcode_names = [insn.name for insn in instructions]
        for i in range(len(opcode_names) - 9):
            window = set(opcode_names[i:i+10])
            if "SLOAD" in window and "CALL" in window:
                approval_then_external_call_pattern = 1
            if "SLOAD" in window and "SSTORE" in window:
                approval_then_state_mutation_pattern = 1
            if approval_then_external_call_pattern and approval_then_state_mutation_pattern:
                break

    # ── Control flow complexity ───────────────────────────────────────────────
    control_flow_complexity_score = (
        opcode_counts.get("JUMPDEST", 0) / bytecode_size
        if bytecode_size > 0 else 0.0
    )

    return {
        "is_verified": int(is_verified),
        "bytecode_size": int(bytecode_size),
        "abi_function_count": int(abi_function_count),
        "external_public_function_count": int(external_public_function_count),
        "approval_related_function_flag": int(approval_related_function_flag),
        "permit_related_function_flag": int(permit_related_function_flag),
        "setApprovalForAll_flag": int(setApprovalForAll_flag),
        "opcode_freq_CALL": float(freq_CALL),
        "opcode_freq_DELEGATECALL": float(freq_DELEGATECALL),
        "opcode_freq_SELFDESTRUCT": float(freq_SELFDESTRUCT),
        "opcode_freq_SSTORE": float(freq_SSTORE),
        "opcode_freq_JUMPI": float(freq_JUMPI),
        "external_call_sites_count": int(external_call_sites_count),
        "has_create2": int(has_create2),
        "proxy_pattern_detected": int(proxy_pattern_detected),
        "approval_then_external_call_pattern": int(approval_then_external_call_pattern),
        "approval_then_state_mutation_pattern": int(approval_then_state_mutation_pattern),
        "control_flow_complexity_score": float(control_flow_complexity_score),
        **(
            _get_slither_features(source_code, compiler_version, address)
            if is_verified == 1
            else _SLITHER_DEFAULTS.copy()
        ),
    }
