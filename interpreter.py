# sys lets this program read command-line arguments.
# Example command:
# python3 interpreter.py examples/helloworld.txt
# In that command, "examples/helloworld.txt" is stored inside sys.argv.
import sys


def resolve_value(token, variables):
    """
    This function figures out what a token means.

    A token can be:
    1. an integer like 5 or -3
    2. a string like "hello"
    3. a variable name like x or name

    The variables dictionary stores values already created by SET or INPUT.
    """

    # First, try to convert the token into an integer.
    # Example: "5" becomes 5.
    # Example: "-3" becomes -3.
    try:
        return int(token)

    # If int(token) fails, that means it is not an integer.
    # We do not stop the program here because it might be a string or variable.
    except ValueError:
        pass

    # Next, check if the token is a string literal.
    # String literals must start and end with double quotes.
    # Example: "hello"
    if len(token) >= 2 and token.startswith('"') and token.endswith('"'):

        # token[1:-1] removes the first and last quote.
        # Example: '"hello"' becomes 'hello'
        return token[1:-1]

    # If it is not an integer or string, treat it as a variable name.
    # Example: if token is "x", check variables["x"].
    if token in variables:
        return variables[token]

    # If the token is not found anywhere, it is an undefined variable.
    raise ValueError(f"Undefined variable '{token}'")


def evaluate_condition(left_token, operator, right_token, variables):
    """
    This function evaluates IF and WHILE conditions.

    Example:
    IF x > 5

    left_token = x
    operator = >
    right_token = 5

    The function returns either True or False.
    """

    # Resolve the left side.
    # Example: x becomes the value stored in variables["x"].
    left_value = resolve_value(left_token, variables)

    # Resolve the right side.
    # Example: 5 becomes integer 5.
    right_value = resolve_value(right_token, variables)

    # Check equal.
    if operator == "==":
        return left_value == right_value

    # Check not equal.
    if operator == "!=":
        return left_value != right_value

    # Check greater than.
    if operator == ">":
        return left_value > right_value

    # Check less than.
    if operator == "<":
        return left_value < right_value

    # Check greater than or equal.
    if operator == ">=":
        return left_value >= right_value

    # Check less than or equal.
    if operator == "<=":
        return left_value <= right_value

    # If the operator is not supported, show an error.
    raise ValueError(f"Invalid comparison operator '{operator}'")


def runtime_error(message):
    """
    This function prints runtime errors in one consistent format.
    Runtime errors happen while the PL-Simple program is running.
    """

    # Print the error message with a clear label.
    print(f"Runtime Error: {message}")


def find_matching_end(lines, start_ip, start_cmd, end_cmd):
    """
    This function scans forward to find the matching END command.

    It is used for:
    - IF ... ENDIF
    - WHILE ... ENDWHILE

    Example:
    IF x > 5
        IF y > 2
        ENDIF
    ENDIF

    The nesting_depth variable makes sure nested blocks work correctly.
    """

    # Start with depth 1 because we are already inside one block.
    nesting_depth = 1

    # Start looking at the line after the current IF or WHILE.
    ip = start_ip + 1

    # Keep scanning while we are inside the source file
    # and have not found the matching end command yet.
    while ip < len(lines) and nesting_depth > 0:

        # Split the current line into tokens.
        tokens = lines[ip].split()

        # The first token is the command.
        command = tokens[0]

        # If we find another start command, this means a nested block begins.
        # Example: IF inside another IF.
        if command == start_cmd:
            nesting_depth += 1

        # If we find an end command, one block has closed.
        elif command == end_cmd:
            nesting_depth -= 1

        # Move to the next line.
        ip += 1

    # If depth is still greater than 0, no matching end was found.
    if nesting_depth > 0:
        return None

    # Return the line index after the matching ENDIF or ENDWHILE.
    return ip


def find_matching_start(lines, end_ip, start_cmd, end_cmd):
    """
    This function scans backward to find the matching start command.

    It is mainly used when the interpreter reaches ENDWHILE.
    At ENDWHILE, the interpreter needs to jump back to the matching WHILE.

    Example:
    WHILE x < 5
        PRINT x
    ENDWHILE

    When we hit ENDWHILE, this function finds the WHILE line.
    """

    # Start with depth 1 because we are currently at one END block.
    nesting_depth = 1

    # Start looking at the line before ENDWHILE.
    ip = end_ip - 1

    # Scan backward until we find the matching WHILE.
    while ip >= 0 and nesting_depth > 0:

        # Split the current line into tokens.
        tokens = lines[ip].split()

        # The first token is the command.
        command = tokens[0]

        # If we find another ENDWHILE while going backward,
        # that means we passed a nested loop ending.
        if command == end_cmd:
            nesting_depth += 1

        # If we find WHILE, we close one nesting level.
        elif command == start_cmd:
            nesting_depth -= 1

        # Move one line backward.
        ip -= 1

    # If depth is still greater than 0, no matching start was found.
    if nesting_depth > 0:
        return None

    # Return the matching start line.
    return ip + 1


def main():
    """
    main() is where the interpreter starts running.

    It:
    1. checks the command-line argument
    2. reads the PL-Simple source file
    3. removes blank lines
    4. executes each line
    """

    # Check if the user provided a source file.
    # sys.argv is a list of command-line parts.
    # Example:
    # python3 interpreter.py examples/helloworld.txt
    #
    # sys.argv[0] = "interpreter.py"
    # sys.argv[1] = "examples/helloworld.txt"
    if len(sys.argv) < 2:

        # If no file is provided, show usage instructions.
        print("Usage: python interpreter.py <source_file>")

        # Stop the program.
        return

    # Store the file path provided by the user.
    source_file = sys.argv[1]

    # Try to open and read the source file.
    try:

        # Open the file using UTF-8 encoding.
        with open(source_file, "r", encoding="utf-8") as file:

            # Read all lines from the file into a list.
            raw_lines = file.readlines()

    # If the file does not exist, show an error.
    except FileNotFoundError:
        runtime_error(f"Source file not found: {source_file}")
        return

    # If another file-reading error happens, show it.
    except OSError as error:
        runtime_error(f"Cannot read source file: {error}")
        return

    # This list will store cleaned source lines.
    source_lines = []

    # Loop through every raw line from the file.
    for line in raw_lines:

        # Remove extra spaces and newline characters.
        stripped = line.strip()

        # Ignore blank lines.
        if stripped:

            # Add non-empty lines to the clean source list.
            source_lines.append(stripped)

    # variables stores all PL-Simple variables.
    # Example after SET x 5:
    # variables = {"x": 5}
    variables = {}

    # ip means instruction pointer.
    # It tells the interpreter which line is currently running.
    # It starts at 0, which is the first line.
    ip = 0

    # Keep running while ip is still inside the program.
    while ip < len(source_lines):

        # Get the current PL-Simple line.
        line = source_lines[ip]

        # Split the line by spaces.
        # Example:
        # SET x 5
        # becomes ["SET", "x", "5"]
        tokens = line.split()

        # The first token is always the command.
        # Example: "SET"
        command = tokens[0]

        # Everything after the command is an argument.
        # Example: ["x", "5"]
        args = tokens[1:]

        # -----------------------------
        # SET command
        # Syntax: SET var value
        # Example: SET x 5
        # -----------------------------
        if command == "SET":

            # SET needs at least two arguments:
            # variable name and value.
            if len(args) < 2:
                runtime_error("SET requires at least 2 arguments: SET var value")
                ip += 1
                continue

            # The first argument is the variable name.
            # Example: x
            var_name = args[0]

            # The rest is the value.
            # join is used so strings with spaces can still work if quoted.
            value_token = " ".join(args[1:])

            try:
                # Resolve the value and store it in the variables dictionary.
                # Example: variables["x"] = 5
                variables[var_name] = resolve_value(value_token, variables)

            except ValueError as error:
                runtime_error(str(error))

            # Move to the next line.
            ip += 1

        # -----------------------------
        # PRINT command
        # Syntax: PRINT value
        # Example: PRINT x
        # Example: PRINT "Hello"
        # -----------------------------
        elif command == "PRINT":

            # PRINT needs at least one value.
            if len(args) < 1:
                runtime_error("PRINT requires a value: PRINT value")
                ip += 1
                continue

            # Combine arguments into one value token.
            value_token = " ".join(args)

            try:
                # Resolve the value.
                # It could be an integer, string, or variable.
                value = resolve_value(value_token, variables)

                # Print the resolved value.
                print(value)

            except ValueError as error:
                runtime_error(str(error))

            # Move to the next line.
            ip += 1

        # -----------------------------
        # INPUT command
        # Syntax: INPUT var
        # Example: INPUT name
        # -----------------------------
        elif command == "INPUT":

            # INPUT needs exactly one variable name.
            if len(args) != 1:
                runtime_error("INPUT requires exactly 1 argument: INPUT var")
                ip += 1
                continue

            # Store the variable name.
            var_name = args[0]

            # Read input from the user.
            user_text = input()

            try:
                # If the input looks like an integer, store it as an int.
                variables[var_name] = int(user_text)

            except ValueError:
                # Otherwise, store it as a string.
                variables[var_name] = user_text

            # Move to the next line.
            ip += 1

        # -----------------------------
        # ADD command
        # Syntax: ADD result a b
        # Example: ADD total x y
        # Meaning: total = x + y
        # -----------------------------
        elif command == "ADD":

            # ADD needs exactly three arguments.
            if len(args) != 3:
                runtime_error("ADD requires exactly 3 arguments: ADD result a b")
                ip += 1
                continue

            # The first argument is where the result will be stored.
            result_name = args[0]

            # The second and third arguments are the values to add.
            token_a = args[1]
            token_b = args[2]

            try:
                # Resolve both operands.
                value_a = resolve_value(token_a, variables)
                value_b = resolve_value(token_b, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # ADD only works with integers.
            if not isinstance(value_a, int) or not isinstance(value_b, int):
                runtime_error("ADD operands must be integers")
                ip += 1
                continue

            # Store the addition result.
            variables[result_name] = value_a + value_b

            # Move to the next line.
            ip += 1

        # -----------------------------
        # MUL command
        # Syntax: MUL result a b
        # Example: MUL answer x y
        # Meaning: answer = x * y
        # -----------------------------
        elif command == "MUL":

            if len(args) != 3:
                runtime_error("MUL requires exactly 3 arguments: MUL result a b")
                ip += 1
                continue

            result_name = args[0]
            token_a = args[1]
            token_b = args[2]

            try:
                value_a = resolve_value(token_a, variables)
                value_b = resolve_value(token_b, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            if not isinstance(value_a, int) or not isinstance(value_b, int):
                runtime_error("MUL operands must be integers")
                ip += 1
                continue

            # Store multiplication result.
            variables[result_name] = value_a * value_b
            ip += 1

        # -----------------------------
        # SUB command
        # Syntax: SUB result a b
        # Example: SUB z x y
        # Meaning: z = x - y
        # -----------------------------
        elif command == "SUB":

            if len(args) != 3:
                runtime_error("SUB requires exactly 3 arguments: SUB result a b")
                ip += 1
                continue

            result_name = args[0]
            token_a = args[1]
            token_b = args[2]

            try:
                value_a = resolve_value(token_a, variables)
                value_b = resolve_value(token_b, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            if not isinstance(value_a, int) or not isinstance(value_b, int):
                runtime_error("SUB operands must be integers")
                ip += 1
                continue

            # Store subtraction result.
            variables[result_name] = value_a - value_b
            ip += 1

        # -----------------------------
        # LEN command
        # Syntax: LEN result value
        # Example: LEN n text
        # Meaning: n = length of text
        # -----------------------------
        elif command == "LEN":

            if len(args) < 2:
                runtime_error("LEN requires at least 2 arguments: LEN result value")
                ip += 1
                continue

            # Variable where length will be stored.
            result_name = args[0]

            # String value to measure.
            value_token = " ".join(args[1:])

            try:
                value = resolve_value(value_token, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # LEN only works on strings.
            if not isinstance(value, str):
                runtime_error("LEN value must be a string")
                ip += 1
                continue

            # Store the string length.
            variables[result_name] = len(value)
            ip += 1

        # -----------------------------
        # CHAR command
        # Syntax: CHAR result value index
        # Example: CHAR ch text 0
        # Meaning: ch = text[0]
        # -----------------------------
        elif command == "CHAR":

            if len(args) < 3:
                runtime_error(
                    "CHAR requires at least 3 arguments: CHAR result value index"
                )
                ip += 1
                continue

            # Variable where the character will be stored.
            result_name = args[0]

            # The string value is everything except result name and index.
            value_token = " ".join(args[1:-1])

            # Last argument is the index.
            index_token = args[-1]

            try:
                # Resolve the string and index.
                value = resolve_value(value_token, variables)
                index = resolve_value(index_token, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # CHAR only works on strings.
            if not isinstance(value, str):
                runtime_error("CHAR value must be a string")
                ip += 1
                continue

            # Index must be an integer.
            if not isinstance(index, int):
                runtime_error("CHAR index must be an integer")
                ip += 1
                continue

            # Index must be inside the string.
            if index < 0 or index >= len(value):
                runtime_error("CHAR index out of range")
                ip += 1
                continue

            # Store the character.
            variables[result_name] = value[index]
            ip += 1

        # -----------------------------
        # CONCAT command
        # Syntax: CONCAT result a b
        # Example: CONCAT full first second
        # Meaning: full = first + second
        # -----------------------------
        elif command == "CONCAT":

            if len(args) != 3:
                runtime_error(
                    "CONCAT requires exactly 3 arguments: CONCAT result a b"
                )
                ip += 1
                continue

            result_name = args[0]
            token_a = args[1]
            token_b = args[2]

            try:
                value_a = resolve_value(token_a, variables)
                value_b = resolve_value(token_b, variables)

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # CONCAT only works on strings.
            if not isinstance(value_a, str) or not isinstance(value_b, str):
                runtime_error("CONCAT operands must be strings")
                ip += 1
                continue

            # Store combined string.
            variables[result_name] = value_a + value_b
            ip += 1

        # -----------------------------
        # IF command
        # Syntax: IF left op right
        # Example: IF x > 5
        #
        # If true, execute the block.
        # If false, skip to matching ENDIF.
        # -----------------------------
        elif command == "IF":

            if len(args) != 3:
                runtime_error("IF requires exactly 3 arguments: IF left op right")
                ip += 1
                continue

            left_token = args[0]
            operator = args[1]
            right_token = args[2]

            try:
                # Evaluate the condition.
                condition_result = evaluate_condition(
                    left_token, operator, right_token, variables
                )

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # If condition is true, continue to the next line.
            if condition_result:
                ip += 1
                continue

            # If condition is false, skip to the matching ENDIF.
            next_ip = find_matching_end(source_lines, ip, "IF", "ENDIF")

            # If no matching ENDIF exists, show an error.
            if next_ip is None:
                runtime_error("Missing ENDIF for IF block")
                ip += 1
                continue

            # Jump to the line after ENDIF.
            ip = next_ip

        # -----------------------------
        # ENDIF command
        # Marks the end of an IF block.
        # It does not do anything by itself.
        # -----------------------------
        elif command == "ENDIF":

            # Move to the next line.
            ip += 1

        # -----------------------------
        # WHILE command
        # Syntax: WHILE left op right
        # Example: WHILE x < 5
        #
        # If true, execute loop body.
        # If false, skip to matching ENDWHILE.
        # -----------------------------
        elif command == "WHILE":

            if len(args) != 3:
                runtime_error(
                    "WHILE requires exactly 3 arguments: WHILE left op right"
                )
                ip += 1
                continue

            left_token = args[0]
            operator = args[1]
            right_token = args[2]

            try:
                # Evaluate the loop condition.
                condition_result = evaluate_condition(
                    left_token, operator, right_token, variables
                )

            except ValueError as error:
                runtime_error(str(error))
                ip += 1
                continue

            # If the condition is true, enter the loop body.
            if condition_result:
                ip += 1
                continue

            # If the condition is false, skip to matching ENDWHILE.
            next_ip = find_matching_end(source_lines, ip, "WHILE", "ENDWHILE")

            if next_ip is None:
                runtime_error("Missing ENDWHILE for WHILE block")
                ip += 1
                continue

            # Jump to the line after ENDWHILE.
            ip = next_ip

        # -----------------------------
        # ENDWHILE command
        # Marks the end of a WHILE loop.
        # It jumps back to the matching WHILE line.
        # -----------------------------
        elif command == "ENDWHILE":

            # Find the WHILE line that matches this ENDWHILE.
            loop_start_ip = find_matching_start(source_lines, ip, "WHILE", "ENDWHILE")

            if loop_start_ip is None:
                runtime_error("ENDWHILE without matching WHILE")
                ip += 1
                continue

            # Jump back to the WHILE line.
            # This causes the WHILE condition to be checked again.
            ip = loop_start_ip

        # -----------------------------
        # Unknown command
        # -----------------------------
        else:

            # If no command matched, the language does not support it.
            runtime_error(f"Unknown command '{command}'")

            # Move to the next line so the interpreter does not freeze.
            ip += 1


# This makes sure main() only runs when this file is executed directly.
# It prevents main() from running automatically if this file is imported.
if __name__ == "__main__":
    main()
