"""
Simple menu driver for the PL-Simple interpreter (class demo).

Runs: python3 interpreter.py <example_file>
"""

import subprocess
import sys
from pathlib import Path


def main():
    # Project root is the folder containing this script (same folder as interpreter.py).
    project_root = Path(__file__).resolve().parent
    interpreter = project_root / "interpreter.py"
    examples_dir = project_root / "examples"

    # Map menu choices to example program paths.
    programs = {
        "1": examples_dir / "helloworld.txt",
        "2": examples_dir / "cat.txt",
        "3": examples_dir / "multiply.txt",
        "4": examples_dir / "is_even.txt",
        "5": examples_dir / "repeater.txt",
        "6": examples_dir / "reverse_string.txt",
        "7": examples_dir / "is_palindrome.txt",
    }

    while True:
        # Show the demo menu.
        print()
        print("PL-Simple Demo Menu")
        print("1. Hello World")
        print("2. Cat (Echo Input)")
        print("3. Multiply")
        print("4. Even or Odd")
        print("5. Repeater")
        print("6. Reverse String")
        print("7. Palindrome")
        print("0. Exit")
        print()

        choice = input("Enter choice: ").strip()

        # Exit the menu loop.
        if choice == "0":
            print("Goodbye!")
            break

        # Unknown menu option.
        if choice not in programs:
            print("Invalid choice. Please try again.")
            continue

        source_file = programs[choice]

        # Make sure the interpreter and example file exist before running.
        if not interpreter.is_file():
            print(f"Error: interpreter not found at {interpreter}")
            continue
        if not source_file.is_file():
            print(f"Error: example not found at {source_file}")
            continue

        # Run the interpreter as a subprocess (same as typing it in the terminal).
        cmd = ["python3", str(interpreter), str(source_file)]
        print()
        print(f"Running: {' '.join(cmd)}")
        print("-" * 40)

        try:
            subprocess.run(cmd, check=False, cwd=str(project_root))
        except OSError as error:
            print(f"Error: could not run subprocess: {error}")

        print("-" * 40)
        print("Done. Returning to menu...")


if __name__ == "__main__":
    main()
