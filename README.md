# PL-Simple Interpreter

PL-Simple is a small custom interpreted language built for learning core programming language concepts.  
This project includes a beginner-friendly Python interpreter and several sample PL-Simple programs.

## Supported Commands

- `SET var value`
- `INPUT var`
- `PRINT value`
- `ADD result a b`
- `MUL result a b`
- `SUB result a b`
- `LEN result value`
- `CHAR result value index`
- `CONCAT result a b`
- `IF left op right`
- `ENDIF`
- `WHILE left op right`
- `ENDWHILE`

## Supported Comparison Operators

- `==`
- `!=`
- `>`
- `<`
- `>=`
- `<=`

## Syntax Rules

- One command per line.
- Lines are split by spaces.
- First token is the command, remaining tokens are arguments.
- Blank lines are ignored.
- String literals use double quotes, for example: `"hello"`.
- Integer literals are values like `5`, `0`, and `-3`.
- Any token that is not an integer literal or string literal is treated as a variable name.

## Run the Interpreter

From the project folder:

```bash
python3 interpreter.py examples/helloworld.txt
```

If no source file is provided, the interpreter prints:

```text
Usage: python interpreter.py <source_file>
```

## Example PL-Simple Snippets

```text
SET x 4
SET y 5
ADD total x y
PRINT total
```

```text
IF total > 5
PRINT "Greater than five"
ENDIF
```

```text
WHILE x < 10
ADD x x 1
ENDWHILE
```

## How the Interpreter Works Internally

- The interpreter reads all source lines from the file.
- It strips whitespace and skips blank lines.
- It executes commands using an instruction pointer (`ip`) that moves through the cleaned lines.
- `resolve_value(...)` converts tokens into integers, strings, or variable values.
- `evaluate_condition(...)` checks comparisons for `IF` and `WHILE`.
- For a false `IF`, the interpreter skips forward to the matching `ENDIF`.
- For a false `WHILE`, it skips forward to the matching `ENDWHILE`.
- At `ENDWHILE`, it jumps back to the matching `WHILE` to evaluate the condition again.

## Code Structure

```text
pl-simple/
├── interpreter.py
├── README.md
└── examples/
    ├── helloworld.txt
    ├── cat.txt
    ├── multiply.txt
    ├── is_even.txt
    ├── repeater.txt
    ├── reverse_string.txt
    ├── is_palindrome.txt
    └── (optional test files)
```

## Extra Credit: PL-Simple to C Transpiler

The extra credit transpiler is implemented in `transpiler.py`. It converts PL-Simple source code into C source code.
It does **not** directly run PL-Simple programs. Instead, it generates a C file named:

```text
output.c
```

### How to transpile an example program

Run:

```bash
python3 transpiler.py examples/test_while.txt
```

This creates:

```text
output.c
```

### How to compile the generated C file

```bash
gcc output.c -o output
```

### How to run the compiled C program

```bash
./output
```

### Full command sequence

```bash
python3 transpiler.py examples/test_while.txt
gcc output.c -o output
./output
```

### Expected output for `examples/test_while.txt`

```text
1
2
3
4
5
```

### Transpiler-supported commands

- `SET`
- `PRINT`
- `ADD`
- `SUB`
- `MUL`
- `IF`
- `ENDIF`
- `WHILE`
- `ENDWHILE`

### Example translation

PL-Simple example:

```text
SET x 1
WHILE x <= 5
PRINT x
ADD x x 1
ENDWHILE
```

Generated C example:

```c
#include <stdio.h>

int main(void) {
    int x = 1;

    while (x <= 5) {
        printf("%d\n", x);
        x = x + 1;
    }

    return 0;
}
```

### Notes and limitations

- This is a simple line-by-line transpiler.
- It assumes valid PL-Simple syntax.
- Unsupported commands such as `INPUT`, `LEN`, `CHAR`, and `CONCAT` are written into `output.c` as comments instead of being silently ignored.
- The interpreter can run all example programs, but the transpiler is mainly to demonstrate translating PL-Simple into C.

## Extra Credit II: LLVM Compiler

`llvm_compiler.py` is an optional second “extra credit” compiler. It reads a **restricted integer-only** subset of PL-Simple, builds **LLVM IR** in memory using **llvmlite**, writes it to `output.ll`, then uses **clang** (with an **llc** fallback) to produce a native executable named `output_llvm`.

This is different from the interpreter: it does **not** execute PL-Simple directly in Python. It generates LLVM IR first, then a small native program you can run from the terminal.

### Required install

```bash
pip3 install llvmlite
```

You also need **clang** (and optionally **llc**) available on your PATH (for example Xcode Command Line Tools on macOS).

### How to compile a program

From the project folder:

```bash
python3 llvm_compiler.py examples/llvm_demo.txt
```

This writes:

- `output.ll` (LLVM IR text)
- `output_llvm` (native executable)

### How to run the executable

```bash
./output_llvm
```

### Expected output for `examples/llvm_demo.txt`

```text
1
2
3
4
5
```

### Supported commands (LLVM compiler subset)

- `SET var integer`
- `PRINT var`
- `PRINT integer`
- `ADD result a b`
- `SUB result a b`
- `MUL result a b`
- `IF left op right`
- `ENDIF`
- `WHILE left op right`
- `ENDWHILE`

### Supported comparison operators

- `==`
- `!=`
- `>`
- `<`
- `>=`
- `<=`

### Limitations

- Only **integer** programs are supported (no string literals, no `INPUT`, no `LEN`, `CHAR`, or `CONCAT`).
- Unsupported commands produce a **clear error** and the compiler exits without overwriting outputs silently.

## GitHub Submission Note

For submission, commit all project files to your GitHub repository, including:

- `interpreter.py`
- `transpiler.py`
- `llvm_compiler.py`
- `demo.py`
- `README.md`
- `examples/` folder

## Course Context

This project was built as a final project for a programming languages class.
