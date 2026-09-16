#!/usr/bin/env python3
"""Generate a synthetic *.r700 fixture used to smoke-test the analyzer."""
import struct
import sys
from pathlib import Path


def be32(v: int) -> bytes:
    return struct.pack(">I", v & 0xFFFFFFFF)


def cf_alu(slot_index: int, count: int, kc0: int = 0, kc1: int = 0) -> bytes:
    w0 = (slot_index & 0x3FFFFF) | ((kc0 & 0xFF) << 24)
    w1 = ((kc1 & 0xFF) << 2) | (((count - 1) & 0x7F) << 10) | (0x08 << 23)
    return be32(w0) + be32(w1)


def cf_export_done(type_: int, base: int, src_gpr: int) -> bytes:
    w0 = (base & 0x3F) | ((type_ & 0x3) << 13)
    w1 = ((src_gpr & 0x7F) << 16) | (0x28 << 23)
    return be32(w0) + be32(w1)


def alu_slot(op11: int, s0_sel: int, s0_ch: int, s1_sel: int, s1_ch: int,
             dst_gpr: int, dst_ch: int) -> bytes:
    w0 = ((s0_sel & 0x1FF)
          | ((s0_ch & 0x3) << 10)
          | ((s1_sel & 0x1FF) << 13)
          | ((s1_ch & 0x3) << 23))
    w1 = ((1 << 4)                      # write
          | ((op11 & 0x7FF) << 7)
          | ((dst_gpr & 0x7F) << 21)
          | ((dst_ch & 0x3) << 29))
    return be32(w0) + be32(w1)


def build_vs():
    """VS with MOV + ADD + one unsupported opcode + EXPORT_DONE POSITION."""
    cf   = cf_alu(2, 3) + cf_export_done(1, 60, 0)
    alu0 = alu_slot(0x19, 0, 0, 0, 0, 0, 0)   # MOV
    alu1 = alu_slot(0x00, 0, 0, 1, 1, 0, 1)   # ADD
    alu2 = alu_slot(0x7A, 0, 0, 0, 0, 0, 2)   # opcode unknown to translator
    return cf + alu0 + alu1 + alu2


def build_ps():
    """PS with MUL + TEX + EXPORT_DONE PIXEL."""
    # CF_TEX at slot index 2 (byte offset 16), count 1
    cf = cf_alu(3, 1)  # ALU at slot 3 (offset 24)
    # CF_TEX
    w0 = (2 & 0x3FFFFF)
    w1 = ((0 & 0x7F) << 10) | (0x01 << 23)  # count=1, CF_TEX
    cf += be32(w0) + be32(w1)
    cf += cf_export_done(0, 0, 1)  # PIXEL export
    # TEX slot (16 bytes) starting at offset 16
    tw0 = (5 << 8)  # resource id 5
    tw1 = 0
    tex = be32(tw0) + be32(tw1) + be32(0) + be32(0)
    # ALU slot at offset 24 + 8 (after TEX 16 bytes) — but our CF_ALU points to
    # slot index 3 (byte offset 24). So ALU must be at offset 24 which is
    # right after cf(24 bytes). We need to lay it out.
    # Actually: 3 CF slots (24 bytes) + 1 TEX slot (16 bytes) = 40, but CF_TEX
    # points to slot 2 (offset 16). Slot 2 (16..31) would be inside CF area.
    # Rework: 3 CF (24 bytes), then TEX (16), then ALU (8).
    # CF_TEX should point to slot index 3 (24 bytes)? Let's fix by writing
    # CF_TEX addr = 3 to land at offset 24.
    #
    # Simpler: rebuild manually.
    pass


def build_ps_simple():
    """PS: 1 ALU (MUL) + EXPORT_DONE PIXEL."""
    cf = cf_alu(2, 1) + cf_export_done(0, 0, 0)
    alu = alu_slot(0x01, 0, 0, 1, 0, 0, 0)   # MUL
    return cf + alu


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/shader_dump_synth")
    out.mkdir(parents=True, exist_ok=True)
    (out / "shader_0000_vs.r700").write_bytes(build_vs())
    (out / "shader_0000_ps.r700").write_bytes(build_ps_simple())
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
