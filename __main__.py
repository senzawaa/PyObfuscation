import argparse
import ast
import io
import random
import time
import tokenize

random.seed(int(time.time()))


def toHex(num):
    return hex(num)


gates = [
    [
        [
            ["0", "0"],
            ["0", "1"],
            ["1", "0"],
        ],
        [
            ["1", "1"]
        ],
        "&"
    ],
    [
        [
            ["0", "0"],
            ["1", "1"],
        ],
        [
            ["1", "0"],
            ["0", "1"],
        ],
        "^"
    ],
    [
        [
            ["0", "0"],
        ],
        [
            ["1", "0"],
            ["0", "1"],
            ["1", "1"],
        ],
        "|"
    ]
]


def toBin(num):
    return bin(num)[2:]


def toNum(binary):
    return int(binary, 2)


def obfuscateNumber(num, lists):
    num = toBin(num)
    b = lists[2]
    a, c = "", ""
    for i, unused in enumerate(num):
        pick = lists[int(num[i])]
        pick = pick[random.randint(0, len(pick) - 1)]
        a, c = a + pick[0], c + pick[1]
    return f"{toHex(int(toNum(a)))}{b}{toHex(int(toNum(c)))}"


def randomGate():
    return gates[random.randint(0, len(gates) - 1)]


def runtimeZero():
    return random.choice(["len([])", "len(())", "len({})", "int(False)"])


def runtimeTrue():
    return f"not(bool({runtimeZero()}))"


def obfuscateRuntimeNumber(num):
    number = obfuscateNumber(num, randomGate())
    zero = runtimeZero()
    wrappers = [
        f"(({number})+({zero}))",
        f"(({number})-({zero}))",
        f"(({number})^({zero}))",
    ]
    return random.choice(wrappers)


def obfuscateBoolean(boolean):
    eq = ["==", "!=", ">", "<", ">=", "<="]
    result = not(boolean)
    a, c = obfuscateNumber(
        random.randint(100, 300),
        randomGate()), obfuscateNumber(random.randint(100, 300), randomGate())

    while result != boolean:
        b = eq[random.randint(0, len(eq) - 1)]
        result = eval(f"({a}){b}({c})")
    return f"({a}){b}({c})"


def obfuscateRuntimeBoolean(boolean):
    return f"(({obfuscateBoolean(boolean)})==({runtimeTrue()}))"


def obfuscateString(string):
    arr = []
    for i, unused in enumerate(string):
        byte = obfuscateNumber(
            ord(string[i]), randomGate())
        falsebyte = obfuscateNumber(
            max(0, ord(string[i]) + random.randint(-10, 10)),
            randomGate(),
        )
        boolean = bool(random.randint(0, 1))
        order = [byte, falsebyte] if boolean else [falsebyte, byte]
        arr.append(
            f"(({obfuscateBoolean(boolean)})and(chr({order[0]}))or(chr({order[1]})))"
        )
    return "+".join(arr) if arr else "''"


def obfuscateAggressiveString(string):
    arr = []
    for i, unused in enumerate(string):
        charnum = ord(string[i])
        key = random.randint(1, 255)
        encoded = charnum ^ key
        encodednum = obfuscateRuntimeNumber(encoded)
        keynum = obfuscateRuntimeNumber(key)
        decoded = f"(({encodednum})^({keynum}))"
        realchar = f"chr({decoded})"
        decoynum = random.randint(0, min(0x10ffff, max(255, charnum + 255)))
        decoychar = f"chr({obfuscateRuntimeNumber(decoynum)})"
        boolean = bool(random.randint(0, 1))
        condition = obfuscateRuntimeBoolean(boolean)
        left, right = [realchar, decoychar] if boolean else [decoychar, realchar]
        arr.append(f"(({left}) if ({condition}) else ({right}))")
    return "+".join(arr) if arr else "''"


def toBase(num, base):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    result = ""
    while num:
        num, remainder = divmod(num, base)
        result = digits[remainder] + result
    return result


class ConstantObfuscator(ast.NodeTransformer):
    def __init__(self, aggressive):
        self.aggressive = aggressive
        super().__init__()

    def obfuscateStringValue(self, value):
        expression = (
            obfuscateAggressiveString(value)
            if self.aggressive
            else obfuscateString(value)
        )
        return ast.parse(expression, mode="eval").body

    def obfuscateIntegerValue(self, value):
        number = abs(value)
        key = self.randomIntegerKey(number)
        encoded = number ^ key
        expression = (
            f"({self.obfuscateIntegerLiteral(encoded)}"
            f"^{self.obfuscateIntegerLiteral(key)})"
        )
        if self.aggressive:
            expression = random.choice([
                f"(({expression})+({runtimeZero()}))",
                f"(({expression})-({runtimeZero()}))",
                f"(({expression})^({runtimeZero()}))",
            ])
        if value < 0:
            expression = f"-({expression})"
        return ast.parse(expression, mode="eval").body

    def randomIntegerKey(self, value):
        key = random.randint(256, max(4096, value + 4096))
        while key == value:
            key = random.randint(256, max(4096, value + 4096))
        return key

    def obfuscateIntegerLiteral(self, value):
        base = random.randint(11, 36)
        while base == value:
            base = random.randint(11, 36)
        return f"int('{toBase(value, base)}',{base})"

    def visit_JoinedStr(self, node):
        return node

    def visit_Match(self, node):
        node.subject = self.visit(node.subject)
        for case in node.cases:
            if case.guard:
                case.guard = self.visit(case.guard)
            self.generic_visit_body(case.body)
        return node

    def visit_Module(self, node):
        self.generic_visit_body(node.body)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit_body(node.body)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword)
        return node

    def visit_FunctionDef(self, node):
        self.visit_function_node(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.visit_function_node(node)
        return node

    def visit_function_node(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.visit_argument_defaults(node.args)
        self.generic_visit_body(node.body)

    def visit_argument_defaults(self, args):
        for i, default in enumerate(args.defaults):
            args.defaults[i] = self.visit(default)
        for i, default in enumerate(args.kw_defaults):
            if default is not None:
                args.kw_defaults[i] = self.visit(default)

    def visit_AnnAssign(self, node):
        node.target = self.visit(node.target)
        if node.value:
            node.value = self.visit(node.value)
        return node

    def generic_visit_body(self, body):
        start = 1 if self.has_docstring(body) else 0
        for i in range(start, len(body)):
            body[i] = self.visit(body[i])

    def has_docstring(self, body):
        return (
            bool(body)
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        )

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(self.obfuscateStringValue(node.value), node)
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return ast.copy_location(self.obfuscateIntegerValue(node.value), node)
        return node


def minifyPythonWhitespace(code):
    lines = []
    currentLine = []
    indentLevel = 0
    tokens = tokenize.generate_tokens(io.StringIO(code).readline)
    for token in tokens:
        if token.type in {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT}:
            continue
        if token.type == tokenize.INDENT:
            indentLevel += 1
            continue
        if token.type == tokenize.DEDENT:
            indentLevel -= 1
            continue
        if token.type == tokenize.NL:
            continue
        if token.type == tokenize.NEWLINE:
            if currentLine:
                lines.append((" " * indentLevel) + minifyTokenLine(currentLine))
                currentLine = []
            continue
        currentLine.append(token)

    if currentLine:
        lines.append((" " * indentLevel) + minifyTokenLine(currentLine))

    return "\n".join(lines)


def minifyTokenLine(tokens):
    parts = []
    previous = None
    for token in tokens:
        if previous and needsSpaceBetween(previous, token):
            parts.append(" ")
        parts.append(token.string)
        previous = token
    return "".join(parts)


def needsSpaceBetween(previous, current):
    if isFStringToken(previous) or isFStringToken(current):
        if previous.string in {
            "and",
            "as",
            "assert",
            "async",
            "case",
            "class",
            "def",
            "del",
            "elif",
            "except",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "match",
            "nonlocal",
            "not",
            "or",
            "raise",
            "return",
            "while",
            "with",
            "yield",
        }:
            return True
        if current.string in {"and", "as", "else", "for", "if", "in", "is", "or"}:
            return True
        if current.type == tokenize.NAME and isFStringToken(previous):
            return True
        if previous.type == tokenize.NAME and isFStringToken(current):
            return True
        return False

    if isWordLike(previous) and isWordLike(current):
        if previous.type == tokenize.STRING and current.type == tokenize.STRING:
            return False
        return True

    if current.string in {
        "and",
        "as",
        "else",
        "for",
        "if",
        "import",
        "in",
        "is",
        "not",
        "or",
    }:
        return previous.string not in {"(", "[", "{", ",", ":", "=", "->"}

    if previous.string in {
        "and",
        "as",
        "assert",
        "async",
        "class",
        "def",
        "del",
        "elif",
        "except",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "match",
        "nonlocal",
        "or",
        "raise",
        "while",
        "with",
        "yield",
    }:
        return current.string not in {"(", "[", "{", ":", ",", ")"}

    if previous.string in {"return", "not", "await"}:
        return isWordLike(current)

    if previous.string == "from":
        return True

    return False


def isWordLike(token):
    tokenName = tokenize.tok_name.get(token.type, "")
    return (
        token.type in {tokenize.NAME, tokenize.NUMBER, tokenize.STRING}
        or tokenName.startswith("FSTRING")
    )


def isFStringToken(token):
    return tokenize.tok_name.get(token.type, "").startswith("FSTRING")


def obfuscateScript(inputPath, outputPath, aggressive):
    with open(inputPath, "r", encoding="utf-8") as source:
        tree = ast.parse(source.read(), filename=inputPath)

    tree = ConstantObfuscator(aggressive).visit(tree)
    ast.fix_missing_locations(tree)

    with open(outputPath, "w", encoding="utf-8") as target:
        target.write(minifyPythonWhitespace(ast.unparse(tree)))
        target.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate strings or Python script constants."
    )
    parser.add_argument("string", nargs="?", help="string to obfuscate")
    parser.add_argument("-i", "--input", help="Python script to obfuscate")
    parser.add_argument("-o", "--output", help="where to write the obfuscated script")
    parser.add_argument(
        "-a",
        "--aggressive",
        action="store_true",
        help="use heavier XOR, runtime noise, and decoy branches",
    )
    args = parser.parse_args()

    if args.input or args.output:
        if args.string:
            parser.error("string mode cannot be combined with --input/--output")
        if not args.input or not args.output:
            parser.error("--input and --output must be used together")
        obfuscateScript(args.input, args.output, args.aggressive)
        return

    if args.string is None:
        parser.error("provide a string or use --input/--output")

    data = (
        obfuscateAggressiveString(args.string)
        if args.aggressive
        else obfuscateString(args.string)
    )
    print(data)


if __name__ == "__main__":
    main()
