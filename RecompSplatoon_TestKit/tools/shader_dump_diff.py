#!/usr/bin/env python3
"""
shader_dump_diff.py — Compare two RECOMP_SHADER_DUMP directories.

Useful when the runtime progresses (e.g. new render context, new milestone)
to see what changed at the shader level.

Emits:
- New shaders present in B but not A (by filename)
- Shaders removed (in A, gone from B)
- Shaders whose bytecode changed (same name, different bytes)
- Opcode-frequency delta (aggregated across all files)
- New/disappeared opcodes

Usage:
    python3 tools/shader_dump_diff.py <dir_A> <dir_B> [--out FILE.md]
"""

import argparse
import hashlib
from collections import Counter
from pathlib import Path
import sys

# Reuse the scanner from shader_opcode_stats.py to keep classification identical.
_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from shader_opcode_stats import scan_shader, analyze_dir  # noqa: E402


def hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dir_a", help="Baseline dump directory")
    ap.add_argument("dir_b", help="New dump directory to compare against A")
    ap.add_argument("--out", help="Write markdown diff to this path")
    args = ap.parse_args()

    A = Path(args.dir_a)
    B = Path(args.dir_b)
    files_a = {p.name: p for p in A.glob("*.r700")}
    files_b = {p.name: p for p in B.glob("*.r700")}

    new    = sorted(set(files_b) - set(files_a))
    gone   = sorted(set(files_a) - set(files_b))
    common = sorted(set(files_a) & set(files_b))

    changed = []
    for name in common:
        ha = hash_file(files_a[name])
        hb = hash_file(files_b[name])
        if ha != hb:
            changed.append((name, ha, hb))

    agg_a = analyze_dir(A)
    agg_b = analyze_dir(B)

    out = []
    out.append("# Shader dump diff")
    out.append("")
    out.append(f"- Baseline: `{A}` ({len(files_a)} files, "
               f"{agg_a['num_alu_slots']} ALU slots)")
    out.append(f"- New:      `{B}` ({len(files_b)} files, "
               f"{agg_b['num_alu_slots']} ALU slots)")
    out.append("")

    out.append(f"## New shaders ({len(new)})")
    for n in new[:50]:
        out.append(f"- {n}")
    if len(new) > 50:
        out.append(f"- ... {len(new) - 50} more")
    out.append("")

    out.append(f"## Removed shaders ({len(gone)})")
    for n in gone[:50]:
        out.append(f"- {n}")
    if len(gone) > 50:
        out.append(f"- ... {len(gone) - 50} more")
    out.append("")

    out.append(f"## Changed bytecode ({len(changed)})")
    for name, ha, hb in changed[:50]:
        out.append(f"- {name}: {ha} → {hb}")
    if len(changed) > 50:
        out.append(f"- ... {len(changed) - 50} more")
    out.append("")

    def delta_table(title, ca: Counter, cb: Counter):
        out.append(f"## {title}")
        out.append("")
        keys = sorted(set(ca) | set(cb))
        rows = [(k, ca.get(k, 0), cb.get(k, 0)) for k in keys]
        rows = [r for r in rows if r[1] != r[2]]
        rows.sort(key=lambda r: -(r[2] - r[1]))
        if not rows:
            out.append("_No changes._")
        else:
            out.append("| Opcode | Before (A) | After (B) | Δ |")
            out.append("| ------ | ---------: | --------: | -:|")
            for k, a, b in rows:
                out.append(f"| 0x{k:02X} | {a} | {b} | {b - a:+d} |")
        out.append("")

    delta_table("CF opcode delta",  agg_a["cf"],      agg_b["cf"])
    delta_table("ALU OP2 delta",    agg_a["alu_op2"], agg_b["alu_op2"])
    delta_table("ALU OP3 delta",    agg_a["alu_op3"], agg_b["alu_op3"])

    md = "\n".join(out)
    if args.out:
        Path(args.out).write_text(md)
        print(f"wrote {args.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
