#!/usr/bin/env python3
"""
Extra Credit II: a tiny PL-Simple -> LLVM IR compiler using llvmlite.

What is LLVM IR?
----------------
LLVM IR is a typed intermediate representation used by the LLVM project.
A compiler can generate LLVM IR as text (.ll files) or as in-memory IR.
Another tool (such as clang) can then compile that IR down to machine code.

This program uses llvmlite's Python API to build LLVM IR in memory, print it
to output.ll, then invokes clang to produce a native executable output_llvm.

How PL-Simple maps to LLVM (high level)
---------------------------------------
- Variables live in stack slots created by alloca (memory for each name).
  Each read is a load; each write is a store. This matches simple C locals and
  avoids SSA phi nodes in a beginner-friendly way.

- Integer literals become i32 constants.

- SET x N           -> store N into alloca for x

- PRINT x / PRINT N -> call printf("%d\n", value) from the C runtime

- ADD r a b       -> t = load(a); u = load(b); store (t+u) into r
  (SUB / MUL similar with sub / mul)

- IF / ENDIF      -> compare with icmp, branch to a "then" block or "merge"
  block; run the then-body; jump to merge.

- WHILE / ENDWHILE -> classic loop: branch to "cond" block; if true go to
  "body", run body, branch back to cond; if false go to "after".

Unsupported PL-Simple features (strings, INPUT, LEN, ...) are rejected with a
clear error so you do not get silent wrong code.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:
    from llvmlite import ir
except ImportError:
    print(
        "Error: llvmlite is not installed.\n"
        "Install it with:\n"
        "  pip3 install llvmlite"
    )
    sys.exit(1)


# --- PL-Simple subset for this compiler ---------------------------------

ALLOWED_COMMANDS = frozenset(
    {
        "SET",
        "PRINT",
        "ADD",
        "SUB",
        "MUL",
        "IF",
        "ENDIF",
        "WHILE",
        "ENDWHILE",
    }
)

COMPARISON_OPS = frozenset({"==", "!=", ">", "<", ">=", "<="})

INT_RE = re.compile(r"^-?\d+$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_int_literal(token: str) -> bool:
    return bool(INT_RE.match(token))


def is_ident(token: str) -> bool:
    return bool(IDENT_RE.match(token))


def read_source_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if s:
            lines.append(s)
    return lines


def validate_program(lines: list[str]) -> None:
    """
    Reject anything outside the supported subset with a clear message.
    """
    for idx, line in enumerate(lines, start=1):
        parts = line.split()
        if not parts:
            continue
        cmd = parts[0]
        if cmd not in ALLOWED_COMMANDS:
            raise ValueError(
                f"Line {idx}: unsupported command '{cmd}' for llvm_compiler "
                f"(only integer subset: SET, PRINT, ADD, SUB, MUL, IF, ENDIF, "
                f"WHILE, ENDWHILE)."
            )

        if any(t.startswith('"') for t in parts):
            raise ValueError(
                f"Line {idx}: string literals are not supported by llvm_compiler "
                f"(integers only): {line!r}"
            )

        if cmd == "SET":
            if len(parts) != 3:
                raise ValueError(f"Line {idx}: SET requires: SET var integer -> {line!r}")
            _, name, val = parts
            if not is_ident(name) or not is_int_literal(val):
                raise ValueError(
                    f"Line {idx}: SET must be 'SET <var> <integer>' only -> {line!r}"
                )

        elif cmd == "PRINT":
            if len(parts) != 2:
                raise ValueError(f"Line {idx}: PRINT requires one operand -> {line!r}")
            _, val = parts
            if not (is_int_literal(val) or is_ident(val)):
                raise ValueError(
                    f"Line {idx}: PRINT must be 'PRINT <var>' or 'PRINT <integer>' -> {line!r}"
                )

        elif cmd in ("ADD", "SUB", "MUL"):
            if len(parts) != 4:
                raise ValueError(
                    f"Line {idx}: {cmd} requires: {cmd} result a b -> {line!r}"
                )
            _, r, a, b = parts
            if not is_ident(r):
                raise ValueError(f"Line {idx}: result must be an identifier -> {line!r}")
            for label, t in (("a", a), ("b", b)):
                if not (is_ident(t) or is_int_literal(t)):
                    raise ValueError(
                        f"Line {idx}: {cmd} operand {label} must be variable or integer -> {line!r}"
                    )

        elif cmd in ("IF", "WHILE"):
            if len(parts) != 4:
                raise ValueError(
                    f"Line {idx}: {cmd} requires: {cmd} left op right -> {line!r}"
                )
            _, left, op, right = parts
            if op not in COMPARISON_OPS:
                raise ValueError(f"Line {idx}: invalid comparison operator {op!r}")
            for label, t in (("left", left), ("right", right)):
                if not (is_ident(t) or is_int_literal(t)):
                    raise ValueError(
                        f"Line {idx}: {cmd} {label} must be variable or integer -> {line!r}"
                    )

        elif cmd in ("ENDIF", "ENDWHILE"):
            if len(parts) != 1:
                raise ValueError(f"Line {idx}: {cmd} must appear alone -> {line!r}")


def collect_variables(lines: list[str]) -> list[str]:
    """All names that need a stack slot (any identifier used as a variable)."""
    names: set[str] = set()
    for line in lines:
        parts = line.split()
        cmd = parts[0]
        if cmd == "SET":
            names.add(parts[1])
        elif cmd == "PRINT" and is_ident(parts[1]):
            names.add(parts[1])
        elif cmd in ("ADD", "SUB", "MUL"):
            names.add(parts[1])
            for t in (parts[2], parts[3]):
                if is_ident(t):
                    names.add(t)
        elif cmd in ("IF", "WHILE"):
            for t in (parts[1], parts[3]):
                if is_ident(t):
                    names.add(t)
    return sorted(names)


def find_matching_close(lines: list[str], open_idx: int, open_cmd: str, close_cmd: str) -> int:
    """Index of the matching close_cmd for open_cmd at open_idx (supports nesting)."""
    depth = 1
    j = open_idx + 1
    while j < len(lines):
        cmd = lines[j].split()[0]
        if cmd == open_cmd:
            depth += 1
        elif cmd == close_cmd:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError(f"No matching {close_cmd} for {open_cmd} at line {open_idx + 1}")


class LLVMCompiler:
    """
    Holds llvmlite IR state: one i32 main(), alloca slots, printf declaration.
    """

    def __init__(self, var_names: list[str]) -> None:
        self.module = ir.Module(name="pl_simple")
        self.int32 = ir.IntType(32)
        self.int8 = ir.IntType(8)
        self.int1 = ir.IntType(1)
        self.ptr_i8 = self.int8.as_pointer()

        # declare i32 @printf(i8*, ...)
        printf_ty = ir.FunctionType(self.int32, [self.ptr_i8], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

        main_ty = ir.FunctionType(self.int32, [])
        self.main_fn = ir.Function(self.module, main_ty, name="main")
        self.entry = self.main_fn.append_basic_block("entry")
        self.builder = ir.IRBuilder(self.entry)

        # Format string global: "%d\n\0"
        fmt_bytes = ("%d\n\0").encode("ascii")
        fmt_arr_ty = ir.ArrayType(self.int8, len(fmt_bytes))
        self.fmt_global = ir.GlobalVariable(self.module, fmt_arr_ty, name="fmt_d_newline")
        self.fmt_global.linkage = "private"
        self.fmt_global.global_constant = True
        self.fmt_global.unnamed_addr = True
        self.fmt_global.initializer = ir.Constant(fmt_arr_ty, bytearray(fmt_bytes))

        # Stack slot for every variable name used in the program.
        self.var_ptr: dict[str, ir.AllocaInstr] = {}
        zero = ir.Constant(self.int32, 0)
        for name in var_names:
            slot = self.builder.alloca(self.int32, name=name)
            self.builder.store(zero, slot)
            self.var_ptr[name] = slot

        self.fmt_ptr = self.builder.bitcast(self.fmt_global, self.ptr_i8)

    def _emit_printf_int(self, value: ir.Value) -> None:
        """Call printf("%d\\n", value); value must be i32."""
        self.builder.call(self.printf, [self.fmt_ptr, value])

    def _load_operand(self, token: str) -> ir.Value:
        if is_int_literal(token):
            return ir.Constant(self.int32, int(token))
        return self.builder.load(self.var_ptr[token])

    def _store(self, name: str, value: ir.Value) -> None:
        self.builder.store(value, self.var_ptr[name])

    def _icmp_condition(self, left_t: str, op: str, right_t: str) -> ir.Value:
        lhs = self._load_operand(left_t)
        rhs = self._load_operand(right_t)
        return self.builder.icmp_signed(op, lhs, rhs)

    def _ensure_terminated(self, block: ir.Block, note: str) -> None:
        if block.terminator is None:
            raise RuntimeError(f"Internal compiler error: block not terminated ({note})")

    def emit_program(self, lines: list[str]) -> None:
        i = 0
        while i < len(lines):
            i = self.emit_statement(lines, i)
        # return 0 from main
        self.builder.ret(ir.Constant(self.int32, 0))

    def emit_statement(self, lines: list[str], i: int) -> int:
        parts = lines[i].split()
        cmd = parts[0]

        if cmd == "SET":
            _, name, val = parts
            self._store(name, ir.Constant(self.int32, int(val)))
            return i + 1

        if cmd == "PRINT":
            _, val = parts
            self._emit_printf_int(self._load_operand(val))
            return i + 1

        if cmd == "ADD":
            _, r, a, b = parts
            va = self._load_operand(a)
            vb = self._load_operand(b)
            self._store(r, self.builder.add(va, vb))
            return i + 1

        if cmd == "SUB":
            _, r, a, b = parts
            va = self._load_operand(a)
            vb = self._load_operand(b)
            self._store(r, self.builder.sub(va, vb))
            return i + 1

        if cmd == "MUL":
            _, r, a, b = parts
            va = self._load_operand(a)
            vb = self._load_operand(b)
            self._store(r, self.builder.mul(va, vb))
            return i + 1

        if cmd == "IF":
            return self.emit_if(lines, i)

        if cmd == "WHILE":
            return self.emit_while(lines, i)

        if cmd in ("ENDIF", "ENDWHILE"):
            raise ValueError(
                f"Line {i + 1}: unexpected {cmd} (should be handled by IF/WHILE lowering)"
            )

        raise ValueError(f"Line {i + 1}: unknown statement {cmd!r}")

    def emit_if(self, lines: list[str], i: int) -> int:
        _, left, op, right = lines[i].split()
        end_if = find_matching_close(lines, i, "IF", "ENDIF")

        then_bb = self.main_fn.append_basic_block("if.then")
        merge_bb = self.main_fn.append_basic_block("if.merge")

        cond = self._icmp_condition(left, op, right)
        self.builder.cbranch(cond, then_bb, merge_bb)

        # Then branch
        self.builder.position_at_end(then_bb)
        j = i + 1
        while j < end_if:
            j = self.emit_statement(lines, j)
        if self.builder.block.terminator is None:
            self.builder.branch(merge_bb)
        self._ensure_terminated(self.builder.block, "if.then")

        # Continue after IF in merge block
        self.builder.position_at_end(merge_bb)
        return end_if + 1

    def emit_while(self, lines: list[str], i: int) -> int:
        _, left, op, right = lines[i].split()
        end_while = find_matching_close(lines, i, "WHILE", "ENDWHILE")

        cond_bb = self.main_fn.append_basic_block("while.cond")
        body_bb = self.main_fn.append_basic_block("while.body")
        after_bb = self.main_fn.append_basic_block("while.after")

        self.builder.branch(cond_bb)

        self.builder.position_at_end(cond_bb)
        cond = self._icmp_condition(left, op, right)
        self.builder.cbranch(cond, body_bb, after_bb)
        self._ensure_terminated(self.builder.block, "while.cond")

        self.builder.position_at_end(body_bb)
        j = i + 1
        while j < end_while:
            j = self.emit_statement(lines, j)
        if self.builder.block.terminator is None:
            self.builder.branch(cond_bb)
        self._ensure_terminated(self.builder.block, "while.body")

        self.builder.position_at_end(after_bb)
        return end_while + 1


def write_ir(module: ir.Module, out_path: Path) -> None:
    out_path.write_text(str(module), encoding="utf-8")


def compile_ll_to_executable(ll_path: Path, exe_path: Path) -> None:
    """
    Turn output.ll into a native executable using clang (preferred on macOS).
    Falls back to llc + clang if clang cannot compile the .ll directly.
    """
    ll_path = ll_path.resolve()
    exe_path = exe_path.resolve()

    try:
        r = subprocess.run(
            ["clang", str(ll_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return
        clang_msg = (r.stderr or r.stdout or "").strip()
    except FileNotFoundError:
        clang_msg = "clang not found"

    # Fallback: llc -> object file -> clang link
    obj_path = ll_path.with_suffix(".o")
    try:
        r1 = subprocess.run(
            ["llc", "-filetype=obj", "-o", str(obj_path), str(ll_path)],
            capture_output=True,
            text=True,
        )
        if r1.returncode != 0:
            raise RuntimeError((r1.stderr or r1.stdout or "llc failed").strip())
        r2 = subprocess.run(
            ["clang", str(obj_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
        )
        if r2.returncode != 0:
            raise RuntimeError((r2.stderr or r2.stdout or "clang link failed").strip())
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Could not compile LLVM IR to an executable.\n"
            f"clang error: {clang_msg}\n"
            f"Also could not run llc/clang fallback ({exc}).\n"
            f"Install Xcode Command Line Tools (macOS) or LLVM/Clang, then retry."
        ) from exc


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 llvm_compiler.py <source_file>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"Error: source file not found: {src}")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent
    out_ll = project_root / "output.ll"
    out_exe = project_root / "output_llvm"

    try:
        lines = read_source_lines(src)
        validate_program(lines)
        var_names = collect_variables(lines)
        compiler = LLVMCompiler(var_names)
        compiler.emit_program(lines)
        write_ir(compiler.module, out_ll)
        compile_ll_to_executable(out_ll, out_exe)
    except ValueError as err:
        print(f"Error: {err}")
        sys.exit(1)
    except RuntimeError as err:
        print(f"Error: {err}")
        sys.exit(1)

    print(f"Wrote LLVM IR: {out_ll}")
    print(f"Built executable: {out_exe}")
    print("Run with:")
    print("  ./output_llvm")


if __name__ == "__main__":
    main()
