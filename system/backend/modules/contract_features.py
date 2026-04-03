from pyevmasm import disassemble_all


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


def compute_contract_features(raw_data: dict) -> dict:
    bytecode_hex: str = raw_data.get("bytecode_hex", "0x") or "0x"
    abi_list: list = raw_data.get("abi_list", []) or []
    is_verified: int = int(raw_data.get("is_verified", 0))

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
        "slither_warning_count_total": 0,
        "slither_low_level_call_count": 0,
        "slither_access_control_issues_count": 0,
    }
