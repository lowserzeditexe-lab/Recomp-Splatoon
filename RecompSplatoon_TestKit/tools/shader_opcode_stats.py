#!/usr/bin/env python3
"""
shader_opcode_stats.py — GPU-independent R700/Latte bytecode analyzer.

Reads all *.r700 files in a directory (produced by RECOMP_SHADER_DUMP) and
produces an opcode frequency report + per-opcode support classification.

Support table below is DERIVED FROM port/os/gx2/r700_to_glsl.cpp
(commit 0b40c4f). Update it in lock-step when the translator gains
new instructions. No opcode is invented — an opcode not listed here is
reported as Missing, exactly the situation the user faces at runtime.

Usage:
    python3 tools/shader_opcode_stats.py <dump_dir> [--out FILE.md]
    python3 tools/shader_opcode_stats.py <dump_dir> --json FILE.json
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# CF opcodes recognized by r700_to_glsl.cpp
# ---------------------------------------------------------------------------
CF_STATUS = {
    0x00: ("CF_NOP",         "Supported"),
    0x01: ("CF_TEX",         "Supported"),
    0x08: ("CF_ALU",         "Supported"),
    0x09: ("CF_ALU_PUSH_BEFORE",   "Supported"),
    0x0A: ("CF_ALU_POP_AFTER",     "Supported"),
    0x0B: ("CF_ALU_POP2_AFTER",    "Supported"),
    0x27: ("CF_EXPORT",      "Supported"),
    0x28: ("CF_EXPORT_DONE", "Supported"),
    0x48: ("CF_ALU_ext",     "Supported"),
    0x49: ("CF_ALU_ext",     "Supported"),
    0x4A: ("CF_ALU_ext",     "Supported"),
    0x4B: ("CF_ALU_ext",     "Supported"),
}

# ALU OP2 opcodes with GLSL emission in r700_to_glsl.cpp
ALU_OP2_STATUS = {
    0x00: ("ADD",         "Supported"),
    0x01: ("MUL",         "Supported"),
    0x02: ("MUL_IEEE",    "Supported"),
    0x03: ("MAX",         "Supported"),
    0x04: ("MIN",         "Supported"),
    0x08: ("FRACT",       "Supported"),
    0x09: ("TRUNC",       "Supported"),
    0x0A: ("CEIL",        "Supported"),
    0x0C: ("FLOOR",       "Supported"),
    0x10: ("FRACT_alt",   "Supported"),
    0x11: ("TRUNC_alt",   "Supported"),
    0x12: ("CEIL_alt",    "Supported"),
    0x14: ("FLOOR_alt",   "Supported"),
    0x19: ("MOV",         "Supported"),
    0x1B: ("SETNE",       "Supported"),
    0x1C: ("SETE",        "Supported"),
    0x20: ("PRED_SETGT",  "Supported"),
    0x21: ("PRED_SETGE",  "Supported"),
    0x50: ("DOT4",        "Partial"),  # emitted as per-component MUL
    0x51: ("DOT4_IEEE",   "Partial"),
    0x61: ("EXP_IEEE",    "Supported"),
    0x62: ("LOG_CLAMPED", "Supported"),
    0x63: ("LOG_IEEE",    "Supported"),
    0x66: ("RECIP",       "Supported"),
    0x69: ("RSQRT",       "Supported"),
    0x6A: ("SQRT",        "Supported"),
    0x6E: ("SIN",         "Partial"),  # normalization π vs 2π needs validation
    0x6F: ("COS",         "Partial"),
}

# ALU OP3 opcodes with GLSL emission (op11 >= 0x200; op3 = (op11>>6) & 0x1F)
ALU_OP3_STATUS = {
    0x10: ("MULADD",      "Supported"),
    0x14: ("MULADD_alt",  "Supported"),
    0x18: ("CNDE",        "Supported"),
    0x19: ("CNDGT",       "Supported"),
    0x1A: ("CNDGE",       "Supported"),
}


# ---------------------------------------------------------------------------
# Big-endian helpers
# ---------------------------------------------------------------------------
def be32(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off:off+4], "big")


def cf_is_alu(op: int) -> bool:
    return (0x08 <= op <= 0x0B) or (0x48 <= op <= 0x4B)


# ---------------------------------------------------------------------------
# Shader scanner — mirrors the Pass-1 scan in r700_to_glsl.cpp
# ---------------------------------------------------------------------------
def scan_shader(data: bytes):
    """Return a dict of counters for one shader blob."""
    stats = {
        "cf": Counter(),
        "alu_op2": Counter(),
        "alu_op3": Counter(),
        "tex_res_ids": Counter(),
        "export_types": Counter(),
        "max_gpr": 0,
        "num_tex_slots": 0,
        "num_alu_slots": 0,
        "num_cf": 0,
        "has_export_done": False,
    }

    off = 0
    while off + 7 < len(data):
        w0 = be32(data, off + 0)
        w1 = be32(data, off + 4)
        op = (w1 >> 23) & 0x7F
        stats["cf"][op] += 1
        stats["num_cf"] += 1

        if cf_is_alu(op):
            addr  = (w0 & 0x3FFFFF) * 8
            count = ((w1 >> 10) & 0x7F) + 1
            end   = min(addr + count * 8, len(data))
            for a in range(addr, end - 7, 8):
                aw0 = be32(data, a + 0)
                aw1 = be32(data, a + 4)
                write = (aw1 >> 4) & 1
                if not write:
                    continue
                op11 = (aw1 >> 7) & 0x7FF
                stats["num_alu_slots"] += 1
                if op11 >= 0x200:
                    op3 = (op11 >> 6) & 0x1F
                    stats["alu_op3"][op3] += 1
                else:
                    stats["alu_op2"][op11] += 1
                g = (aw1 >> 21) & 0x7F
                if g > stats["max_gpr"]:
                    stats["max_gpr"] = g
            off += 8
        elif op == 0x01:  # CF_TEX
            addr  = (w0 & 0x3FFFFF) * 8
            count = ((w1 >> 10) & 0x7F) + 1
            end   = min(addr + count * 16, len(data))
            for a in range(addr, end - 15, 16):
                tw0 = be32(data, a + 0)
                rid = (tw0 >> 8) & 0xFF
                stats["tex_res_ids"][rid] += 1
                stats["num_tex_slots"] += 1
            off += 8
        elif op in (0x27, 0x28):  # CF_EXPORT / CF_EXPORT_DONE
            exp_type = (w0 >> 13) & 0x3
            stats["export_types"][exp_type] += 1
            if op == 0x28:
                stats["has_export_done"] = True
                break
            off += 8
        else:
            off += 8

    return stats


# ---------------------------------------------------------------------------
# Aggregation across all *.r700 files
# ---------------------------------------------------------------------------
def analyze_dir(dump_dir: Path):
    files = sorted(dump_dir.glob("*.r700"))
    agg = {
        "shader_count": 0,
        "vs_count": 0,
        "ps_count": 0,
        "empty_or_invalid": 0,
        "cf": Counter(),
        "alu_op2": Counter(),
        "alu_op3": Counter(),
        "tex_res_ids": Counter(),
        "export_types": Counter(),
        "num_alu_slots": 0,
        "num_tex_slots": 0,
        "max_gpr_seen": 0,
        "shaders_missing_export_done": [],
        "per_shader": [],
    }

    for path in files:
        data = path.read_bytes()
        if len(data) < 8:
            agg["empty_or_invalid"] += 1
            continue
        s = scan_shader(data)
        agg["shader_count"] += 1
        if path.stem.endswith("_vs"):
            agg["vs_count"] += 1
        elif path.stem.endswith("_ps"):
            agg["ps_count"] += 1
        agg["cf"] += s["cf"]
        agg["alu_op2"] += s["alu_op2"]
        agg["alu_op3"] += s["alu_op3"]
        agg["tex_res_ids"] += s["tex_res_ids"]
        agg["export_types"] += s["export_types"]
        agg["num_alu_slots"] += s["num_alu_slots"]
        agg["num_tex_slots"] += s["num_tex_slots"]
        agg["max_gpr_seen"] = max(agg["max_gpr_seen"], s["max_gpr"])
        if not s["has_export_done"]:
            agg["shaders_missing_export_done"].append(path.name)
        agg["per_shader"].append({"file": path.name, "stats": {
            "cf":         dict(s["cf"]),
            "alu_op2":    dict(s["alu_op2"]),
            "alu_op3":    dict(s["alu_op3"]),
            "tex_res_ids": dict(s["tex_res_ids"]),
            "export_types": dict(s["export_types"]),
            "num_alu_slots": s["num_alu_slots"],
            "num_tex_slots": s["num_tex_slots"],
            "max_gpr": s["max_gpr"],
        }})
    return agg


# ---------------------------------------------------------------------------
# Report emitters
# ---------------------------------------------------------------------------
def classify(op: int, table: dict, category: str):
    if op in table:
        name, status = table[op]
        return f"{category}/{name}", status
    return f"{category}/0x{op:02X}", "Missing"


def emit_md(agg, dump_dir: Path) -> str:
    lines = []
    lines.append("# R700_SPLATOON_OPCODE_STATS — Auto-generated")
    lines.append("")
    lines.append(f"Source directory: `{dump_dir}`")
    lines.append(f"Shader count: **{agg['shader_count']}** "
                 f"(VS: {agg['vs_count']}, PS: {agg['ps_count']}, "
                 f"invalid: {agg['empty_or_invalid']})")
    lines.append(f"ALU slots total: **{agg['num_alu_slots']}**")
    lines.append(f"TEX slots total: **{agg['num_tex_slots']}**")
    lines.append(f"Max GPR seen: **r[{agg['max_gpr_seen']}]**")
    if agg["shaders_missing_export_done"]:
        lines.append("")
        lines.append(f"⚠ **{len(agg['shaders_missing_export_done'])} shaders "
                     "without CF_EXPORT_DONE terminator** — first 10:")
        for f in agg["shaders_missing_export_done"][:10]:
            lines.append(f"- `{f}`")
    lines.append("")

    def table_section(title, counter, status_table, category):
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Opcode | Name | Count | Status |")
        lines.append("| ------ | ---- | -----:| :-----:|")
        # sort by count desc, then opcode asc
        for op, cnt in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            full_name, status = classify(op, status_table, category)
            name = full_name.split("/", 1)[1]
            emoji = {"Supported": "✅", "Partial": "⚠️", "Missing": "❌"}[status]
            lines.append(f"| 0x{op:02X} | {name} | {cnt} | {emoji} {status} |")
        lines.append("")

    table_section("CF opcodes",  agg["cf"],      CF_STATUS,      "CF")
    table_section("ALU OP2",     agg["alu_op2"], ALU_OP2_STATUS, "OP2")
    table_section("ALU OP3",     agg["alu_op3"], ALU_OP3_STATUS, "OP3")

    # Export types
    lines.append("## Export types")
    lines.append("")
    exp_names = {0: "PIXEL", 1: "POSITION", 2: "PARAMETER"}
    lines.append("| Type | Name | Count |")
    lines.append("| ---- | ---- | -----:|")
    for t, cnt in sorted(agg["export_types"].items()):
        lines.append(f"| {t} | {exp_names.get(t, f'0x{t:X}')} | {cnt} |")
    lines.append("")

    # Texture resource ids
    if agg["tex_res_ids"]:
        lines.append("## Texture resource IDs used")
        lines.append("")
        lines.append("| Res ID | Count |")
        lines.append("| ------ | -----:|")
        for rid, cnt in sorted(agg["tex_res_ids"].items()):
            lines.append(f"| {rid} | {cnt} |")
        lines.append("")

    # Missing summary — highest priority actionable list
    missing = []
    for op, cnt in agg["alu_op2"].items():
        if op not in ALU_OP2_STATUS:
            missing.append(("OP2", op, cnt))
    for op, cnt in agg["alu_op3"].items():
        if op not in ALU_OP3_STATUS:
            missing.append(("OP3", op, cnt))
    for op, cnt in agg["cf"].items():
        if op not in CF_STATUS:
            missing.append(("CF", op, cnt))
    lines.append("## Missing opcodes — implementation priority (highest count first)")
    lines.append("")
    if not missing:
        lines.append("_All observed opcodes already have translator entries._")
    else:
        missing.sort(key=lambda x: -x[2])
        lines.append("| Category | Opcode | Count |")
        lines.append("| -------- | ------ | -----:|")
        for cat, op, cnt in missing:
            lines.append(f"| {cat} | 0x{op:02X} | {cnt} |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dump_dir", help="Directory containing *.r700 files")
    ap.add_argument("--out", help="Write markdown report to this path")
    ap.add_argument("--json", help="Write JSON stats to this path")
    args = ap.parse_args()

    dump = Path(args.dump_dir)
    if not dump.is_dir():
        print(f"error: {dump} is not a directory", file=sys.stderr)
        sys.exit(2)

    agg = analyze_dir(dump)
    md = emit_md(agg, dump)

    if args.out:
        Path(args.out).write_text(md)
        print(f"wrote {args.out}")
    else:
        print(md)

    if args.json:
        # Counter -> dict, sort keys
        j = {
            "shader_count": agg["shader_count"],
            "vs_count": agg["vs_count"],
            "ps_count": agg["ps_count"],
            "empty_or_invalid": agg["empty_or_invalid"],
            "num_alu_slots": agg["num_alu_slots"],
            "num_tex_slots": agg["num_tex_slots"],
            "max_gpr_seen": agg["max_gpr_seen"],
            "cf":            {f"0x{k:02X}": v for k, v in sorted(agg["cf"].items())},
            "alu_op2":       {f"0x{k:02X}": v for k, v in sorted(agg["alu_op2"].items())},
            "alu_op3":       {f"0x{k:02X}": v for k, v in sorted(agg["alu_op3"].items())},
            "tex_res_ids":   {str(k): v for k, v in sorted(agg["tex_res_ids"].items())},
            "export_types":  {str(k): v for k, v in sorted(agg["export_types"].items())},
            "shaders_missing_export_done": agg["shaders_missing_export_done"],
            "per_shader": agg["per_shader"],
        }
        Path(args.json).write_text(json.dumps(j, indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
