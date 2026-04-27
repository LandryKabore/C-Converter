"""
Reads a PL-Simple source file line by line, translates supported commands
to C, and writes output.c. No lexer/parser frameworks — just split() and
simple string checks, similar to the interpreter.
"""

import sys
from pathlib import Path


def is_int_literal(token):
    """True if token looks like a signed integer literal."""
    if token in ("", "+", "-"):
        return False
    if token[0] in "+-":
        token = token[1:]
    return token.isdigit()


def is_string_literal(token):
    """True if token is a full double-quoted PL-Simple string."""
    return len(token) >= 2 and token[0] == '"' and token[-1] == '"'


def c_escape_string(inner):
    """Escape content for a C string literal."""
    return inner.replace("\\", "\\\\").replace('"', '\\"')


def classify_value_token(value_token, var_types):
    """
    Decide how a single PL-Simple value token becomes a C expression fragment.

    Returns (kind, c_expr) where kind is 'int' or 'str'.
    """
    if is_int_literal(value_token):
        return "int", value_token

    if is_string_literal(value_token):
        inner = value_token[1:-1]
        return "str", f'"{c_escape_string(inner)}"'

    # Variable reference — type must be known from earlier SET.
    if value_token in var_types:
        kind = var_types[value_token]
        return kind, value_token

    # Unknown variable: still emit something so the file is visible; C may error.
    return "int", value_token


def translate_line(line, var_types, declared, lines_out, indent):
    """
    Translate one non-empty PL-Simple line into zero or more C lines.

    var_types: name -> 'int' or 'str'
    declared: set of variable names already declared in C
    lines_out: list of C lines we append to (each line includes `indent` prefix)
    indent: spaces for this line (main body + nested IF/WHILE blocks)
    """
    tokens = line.split()
    if not tokens:
        return

    cmd = tokens[0]
    args = tokens[1:]

    # --- SET var value ---
    if cmd == "SET":
        if len(args) < 2:
            lines_out.append(f"{indent}// ERROR: SET needs var and value")
            return
        var_name = args[0]
        value_token = " ".join(args[1:])

        # PL-Simple allows only one "value" token for transpiler simplicity here.
        if " " in value_token.strip() and not (
            value_token.startswith('"') and value_token.endswith('"')
        ):
            lines_out.append(
                f"{indent}// ERROR: SET value must be a single token or one string literal"
            )
            return

        kind, c_expr = classify_value_token(value_token.strip(), var_types)

        if var_name not in declared:
            if kind == "int":
                lines_out.append(f"{indent}int {var_name} = {c_expr};")
            else:
                lines_out.append(f"{indent}const char *{var_name} = {c_expr};")
            declared.add(var_name)
            var_types[var_name] = kind
        else:
            lines_out.append(f"{indent}{var_name} = {c_expr};")
        return

    # --- PRINT value ---
    if cmd == "PRINT":
        if len(args) < 1:
            lines_out.append(f"{indent}// ERROR: PRINT needs a value")
            return
        value_token = " ".join(args)

        if is_string_literal(value_token):
            inner = value_token[1:-1]
            lines_out.append(
                f'{indent}printf("{c_escape_string(inner)}\\n");'
            )
            return

        if is_int_literal(value_token):
            lines_out.append(f'{indent}printf("%d\\n", {value_token});')
            return

        if value_token in var_types:
            if var_types[value_token] == "int":
                lines_out.append(f'{indent}printf("%d\\n", {value_token});')
            else:
                lines_out.append(f'{indent}printf("%s\\n", {value_token});')
            return

        # Unknown: assume int for simple demos
        lines_out.append(f'{indent}printf("%d\\n", {value_token});')
        return

    # --- ADD / SUB / MUL result a b ---
    if cmd in ("ADD", "SUB", "MUL"):
        if len(args) != 3:
            lines_out.append(f"{indent}// ERROR: {cmd} needs result a b")
            return
        result, a, b = args
        op = {"ADD": "+", "SUB": "-", "MUL": "*"}[cmd]
        rhs = f"{a} {op} {b}"

        if result not in declared:
            lines_out.append(f"{indent}int {result} = {rhs};")
            declared.add(result)
            var_types[result] = "int"
        else:
            lines_out.append(f"{indent}{result} = {rhs};")
        return

    # --- IF a op b ---
    if cmd == "IF":
        if len(args) != 3:
            lines_out.append(f"{indent}// ERROR: IF needs left op right")
            return
        left, op, right = args
        lines_out.append(f"{indent}if ({left} {op} {right}) {{")
        return

    # --- ENDIF ---
    if cmd == "ENDIF":
        lines_out.append(f"{indent}}}")
        return

    # --- WHILE a op b ---
    if cmd == "WHILE":
        if len(args) != 3:
            lines_out.append(f"{indent}// ERROR: WHILE needs left op right")
            return
        left, op, right = args
        lines_out.append(f"{indent}while ({left} {op} {right}) {{")
        return

    # --- ENDWHILE ---
    if cmd == "ENDWHILE":
        lines_out.append(f"{indent}}}")
        return

    # Anything else: leave a comment so the student can see skipped lines.
    safe = line.replace("*/", "* /")
    lines_out.append(f"{indent}// UNSUPPORTED: {safe}")


def transpile(source_lines):
    """
    Turn cleaned PL-Simple lines into C source (body of main only).

    Line-by-line idea (no real parser):
    - Each PL command becomes one C statement (or one control line with '{').
    - IF/WHILE end with '{' on the same line (C style).
    - ENDIF / ENDWHILE become a single closing '}'.
    - We track brace_depth so each nested block gets deeper indentation.

    Note: Only the commands listed in the assignment are translated in full;
    other PL lines become // UNSUPPORTED comments so you can still see them.
    """
    var_types = {}
    declared = set()
    body_lines = []
    brace_depth = 0
    base = "    "

    for raw in source_lines:
        line = raw.strip()
        if not line:
            continue

        tokens = line.split()
        cmd = tokens[0]

        # Closing keywords reduce logical depth *before* we emit their line,
        # so the closing '}' aligns with the opening if/while.
        if cmd in ("ENDIF", "ENDWHILE"):
            brace_depth = max(0, brace_depth - 1)

        indent = base * (1 + brace_depth)
        translate_line(line, var_types, declared, body_lines, indent)

        if cmd in ("IF", "WHILE"):
            brace_depth += 1

    return body_lines


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 transpiler.py <source_file>")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.is_file():
        print(f"Error: source file not found: {source_path}")
        sys.exit(1)

    text = source_path.read_text(encoding="utf-8")
    source_lines = text.splitlines()

    body = transpile(source_lines)

    out = []
    out.append("#include <stdio.h>")
    out.append("")
    out.append("int main(void) {")
    out.extend(body)
    out.append("    return 0;")
    out.append("}")
    out.append("")

    out_path = Path("output.c")
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
