// tests/test_r700_to_glsl.cpp
//
// Minimal, GPU-independent unit tests for the R700 -> GLSL translator.
// These tests do NOT validate that the produced GLSL compiles on a real GL
// driver — that requires a Windows / Linux GPU box (see docs/R700_GLSL_AUDIT.md
// §7 for the shader dump env vars and validation procedure).
//
// Build (standalone, no CMake target added yet — invoked manually):
//     g++ -std=c++20 -I../../vendor/rebrewu/port/os/gx2 \
//         tests/test_r700_to_glsl.cpp \
//         ../../vendor/rebrewu/port/os/gx2/r700_to_glsl.cpp \
//         -o /tmp/test_r700_to_glsl
//
// The tests are pure C++, do not include any RebrewU runtime header, and
// operate on hand-crafted big-endian R700 CF/ALU/TEX bytecode blobs.

#include "r700_to_glsl.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// ---------------------------------------------------------------------------
// Helpers to build big-endian R700 CF words and ALU/TEX slots
// ---------------------------------------------------------------------------
static void write_be32(uint8_t* p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >>  8);
    p[3] = (uint8_t) v;
}

// CF_ALU word0/word1 (approx layout used by the translator):
//   WORD0[21:0] = alu clause byte-addr / 8
//   WORD0[31:24] = kc0
//   WORD1[9:2]  = kc1
//   WORD1[16:10] = count-1
//   WORD1[29:23] = cf_op   (0x08 = CF_ALU)
static void encode_cf_alu(uint8_t* out, uint32_t alu_slot_index,
                          uint32_t slot_count, uint32_t kc0, uint32_t kc1) {
    uint32_t w0 = (alu_slot_index & 0x3FFFFFu) | ((kc0 & 0xFFu) << 24);
    uint32_t w1 = ((kc1 & 0xFFu) << 2)
                | (((slot_count - 1u) & 0x7Fu) << 10)
                | (0x08u << 23);
    write_be32(out + 0, w0);
    write_be32(out + 4, w1);
}

// CF_EXPORT_DONE word0/word1:
//   WORD0[5:0]   = ARRAY_BASE
//   WORD0[14:13] = TYPE (0=PIXEL, 1=POSITION, 2=PARAMETER)
//   WORD1[22:16] = SRC_GPR
//   WORD1[29:23] = 0x28 (CF_EXPORT_DONE)
static void encode_cf_export_done(uint8_t* out,
                                  uint32_t type, uint32_t base,
                                  uint32_t src_gpr) {
    uint32_t w0 = (base & 0x3Fu) | ((type & 0x3u) << 13);
    uint32_t w1 = ((src_gpr & 0x7Fu) << 16) | (0x28u << 23);
    write_be32(out + 0, w0);
    write_be32(out + 4, w1);
}

// ALU slot (2 words = 8 bytes):
//   WORD0[8:0]   = src0 sel
//   WORD0[11:10] = src0 chan
//   WORD0[12]    = src0 neg
//   WORD0[21:13] = src1 sel
//   WORD0[24:23] = src1 chan
//   WORD0[25]    = src1 neg
//   WORD1[4]     = write
//   WORD1[17:7]  = op11 (op2 if <0x200, op3 if >=0x200)
//   WORD1[27:21] = dst_gpr
//   WORD1[30:29] = dst_chan
//   WORD1[31]    = clamp
static void encode_alu_slot(uint8_t* out,
                            uint32_t op11,
                            uint32_t s0_sel, uint32_t s0_ch, bool s0_neg,
                            uint32_t s1_sel, uint32_t s1_ch, bool s1_neg,
                            uint32_t dst_gpr, uint32_t dst_ch,
                            bool write, bool clamp) {
    uint32_t w0 = (s0_sel & 0x1FFu)
                | ((s0_ch & 0x3u) << 10)
                | ((s0_neg ? 1u : 0u) << 12)
                | ((s1_sel & 0x1FFu) << 13)
                | ((s1_ch & 0x3u) << 23)
                | ((s1_neg ? 1u : 0u) << 25);
    uint32_t w1 = ((write ? 1u : 0u) << 4)
                | ((op11 & 0x7FFu) << 7)
                | ((dst_gpr & 0x7Fu) << 21)
                | ((dst_ch & 0x3u) << 29)
                | ((clamp ? 1u : 0u) << 31);
    write_be32(out + 0, w0);
    write_be32(out + 4, w1);
}

// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------
static int g_pass = 0, g_fail = 0;

#define EXPECT(cond, msg) do {                                              \
    if (cond) { g_pass++; }                                                 \
    else { g_fail++; fprintf(stderr, "FAIL %s:%d: %s\n",                    \
                              __FILE__, __LINE__, msg); }                   \
} while (0)

static bool contains(const char* hay, const char* needle) {
    return hay && needle && strstr(hay, needle) != nullptr;
}

// ---------------------------------------------------------------------------
// Test 1: empty shader (only EXPORT_DONE) — must not crash, must emit main()
// ---------------------------------------------------------------------------
static void test_empty_export_only() {
    uint8_t buf[8];
    encode_cf_export_done(buf, /*type=*/1, /*base=*/60, /*src=*/0);
    R700TranslateInput in{};
    in.data = buf; in.size = sizeof(buf);
    in.is_pixel = false; in.num_attribs = 0;

    char* g = r700_to_glsl(in);
    EXPECT(g != nullptr,                "empty shader must not return null");
    EXPECT(contains(g, "#version 410 core"), "must emit #version 410 core");
    EXPECT(contains(g, "void main()"),  "must emit main()");
    EXPECT(contains(g, "gl_Position = r[0];"), "POSITION export must map to gl_Position");
    free(g);
}

// ---------------------------------------------------------------------------
// Test 2: VS UBO binding = 0, PS UBO binding = 1
// ---------------------------------------------------------------------------
static void test_ubo_binding_split() {
    uint8_t buf[8];
    encode_cf_export_done(buf, /*type=*/1, /*base=*/60, /*src=*/0);
    R700TranslateInput vs{}, ps{};
    vs.data = ps.data = buf; vs.size = ps.size = sizeof(buf);
    vs.is_pixel = false; vs.num_attribs = 0;
    ps.is_pixel = true;  ps.num_attribs = 0;

    char* gvs = r700_to_glsl(vs);
    char* gps = r700_to_glsl(ps);
    EXPECT(contains(gvs, "layout(std140, binding=0)"), "VS must bind UBO at 0");
    EXPECT(contains(gps, "layout(std140, binding=1)"), "PS must bind UBO at 1");
    free(gvs); free(gps);
}

// ---------------------------------------------------------------------------
// Test 3: ALU MOV — must emit `r[dst].chan = r[src].chan;`
// ---------------------------------------------------------------------------
static void test_alu_mov() {
    // Layout: [0..15] = 2 CF slots (ALU + EXPORT_DONE)
    //         [16..23] = 1 ALU slot
    uint8_t buf[16 + 8];
    memset(buf, 0, sizeof(buf));
    // CF_ALU pointing at alu_slot_index = 2 (byte offset 16 / 8 = 2), count=1
    encode_cf_alu(buf + 0, /*alu_slot=*/2, /*count=*/1, /*kc0=*/0, /*kc1=*/0);
    encode_cf_export_done(buf + 8, /*type=*/1, /*base=*/60, /*src=*/1);
    // ALU MOV r[1].x = r[0].y
    encode_alu_slot(buf + 16,
                    /*op11=*/0x19, // MOV
                    /*s0_sel=*/0, /*s0_ch=*/1, /*s0_neg=*/false,
                    /*s1_sel=*/0, /*s1_ch=*/0, /*s1_neg=*/false,
                    /*dst_gpr=*/1, /*dst_ch=*/0,
                    /*write=*/true, /*clamp=*/false);

    R700TranslateInput in{};
    in.data = buf; in.size = sizeof(buf);
    in.is_pixel = false; in.num_attribs = 0;

    char* g = r700_to_glsl(in);
    EXPECT(g != nullptr, "MOV shader must not return null");
    EXPECT(contains(g, "r[1].x = "), "must write to r[1].x");
    EXPECT(contains(g, "r[0].y"),     "must read r[0].y");
    free(g);
}

// ---------------------------------------------------------------------------
// Test 4: Unsupported opcode must produce a debug comment, not crash
// ---------------------------------------------------------------------------
static void test_unknown_opcode_yields_comment() {
    uint8_t buf[16 + 8];
    memset(buf, 0, sizeof(buf));
    encode_cf_alu(buf + 0, 2, 1, 0, 0);
    encode_cf_export_done(buf + 8, 1, 60, 0);
    // Use opcode 0x7A — currently not implemented in the switch
    encode_alu_slot(buf + 16,
                    /*op11=*/0x7A,
                    /*s0_sel=*/0, /*s0_ch=*/0, false,
                    /*s1_sel=*/0, /*s1_ch=*/0, false,
                    /*dst_gpr=*/0, /*dst_ch=*/0,
                    /*write=*/true, /*clamp=*/false);

    R700TranslateInput in{};
    in.data = buf; in.size = sizeof(buf);
    in.is_pixel = false; in.num_attribs = 0;

    char* g = r700_to_glsl(in);
    EXPECT(g != nullptr, "unknown opcode must not crash");
    EXPECT(contains(g, "/*op2=0x7A*/"), "must emit /*op2=0xXX*/ marker for unsupported");
    free(g);
}

// ---------------------------------------------------------------------------
// Test 5: Pixel shader export type=0 must produce frag_color
// ---------------------------------------------------------------------------
static void test_pixel_export() {
    uint8_t buf[8];
    encode_cf_export_done(buf, /*type=*/0, /*base=*/0, /*src=*/2);
    R700TranslateInput in{};
    in.data = buf; in.size = sizeof(buf);
    in.is_pixel = true; in.num_attribs = 0;

    char* g = r700_to_glsl(in);
    EXPECT(g != nullptr, "pixel export must not return null");
    EXPECT(contains(g, "out vec4 frag_color"), "PS must declare frag_color out");
    EXPECT(contains(g, "frag_color = r[2];"),  "PS PIXEL export must map to frag_color");
    free(g);
}

// ---------------------------------------------------------------------------
// Test 6: Invalid input (null / too small) must return nullptr
// ---------------------------------------------------------------------------
static void test_invalid_input() {
    R700TranslateInput in{};
    in.data = nullptr; in.size = 0;
    char* g = r700_to_glsl(in);
    EXPECT(g == nullptr, "null data must return nullptr");

    uint8_t tiny[4] = {0,0,0,0};
    in.data = tiny; in.size = sizeof(tiny);
    g = r700_to_glsl(in);
    EXPECT(g == nullptr, "size<8 must return nullptr");
}

// ---------------------------------------------------------------------------
// Test 7: Vertex attribs declaration
// ---------------------------------------------------------------------------
static void test_vertex_attribs() {
    uint8_t buf[8];
    encode_cf_export_done(buf, /*type=*/1, /*base=*/60, /*src=*/0);
    R700TranslateInput in{};
    in.data = buf; in.size = sizeof(buf);
    in.is_pixel = false; in.num_attribs = 3;

    char* g = r700_to_glsl(in);
    EXPECT(contains(g, "layout(location=0) in vec4 a0;"), "must declare a0");
    EXPECT(contains(g, "layout(location=1) in vec4 a1;"), "must declare a1");
    EXPECT(contains(g, "layout(location=2) in vec4 a2;"), "must declare a2");
    EXPECT(!contains(g, "layout(location=3)"),            "must not declare a3 (num_attribs=3)");
    EXPECT(contains(g, "r[0] = a0;"), "must load a0 into r[0]");
    free(g);
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------
int main() {
    test_empty_export_only();
    test_ubo_binding_split();
    test_alu_mov();
    test_unknown_opcode_yields_comment();
    test_pixel_export();
    test_invalid_input();
    test_vertex_attribs();

    fprintf(stderr, "\ntest_r700_to_glsl: %d passed, %d failed\n",
            g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
