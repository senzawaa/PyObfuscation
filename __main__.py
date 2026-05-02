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


class StringConstantObfuscator(ast.NodeTransformer):
    def __init__(self, aggressive):
        self.aggressive = aggressive
        super().__init__()

    def obfuscateValue(self, value):
        expression = (
            obfuscateAggressiveString(value)
            if self.aggressive
            else obfuscateString(value)
        )
        return ast.parse(expression, mode="eval").body

    def visit_JoinedStr(self, node):
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
        if not isinstance(node.value, str):
            return node
        return ast.copy_location(self.obfuscateValue(node.value), node)


def compactArithmeticWhitespace(code):
    compactOperators = {
        "+",
        "-",
        "*",
        "/",
        "//",
        "%",
        "**",
        "&",
        "|",
        "^",
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
    }
    tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    lines = code.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(position):
        row, column = position
        return offsets[row - 1] + column

    def compactWhitespace(value):
        if "\n" not in value and "\r" not in value:
            return ""
        return "\n".join(part.strip(" \t") for part in value.split("\n"))

    result = []
    lastOffset = 0
    previousOperator = False
    for token in tokens:
        if token.type == tokenize.ENDMARKER:
            continue
        start = offset(token.start)
        end = offset(token.end)
        currentOperator = token.type == tokenize.OP and token.string in compactOperators
        whitespace = code[lastOffset:start]
        if previousOperator or currentOperator:
            whitespace = compactWhitespace(whitespace)
        result.append(whitespace)
        result.append(token.string)
        lastOffset = end
        previousOperator = currentOperator
    result.append(code[lastOffset:])
    return "".join(result)


def obfuscateScript(inputPath, outputPath, aggressive):
    with open(inputPath, "r", encoding="utf-8") as source:
        tree = ast.parse(source.read(), filename=inputPath)

    tree = StringConstantObfuscator(aggressive).visit(tree)
    ast.fix_missing_locations(tree)

    with open(outputPath, "w", encoding="utf-8") as target:
        target.write(compactArithmeticWhitespace(ast.unparse(tree)))
        target.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate strings or Python script string constants."
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
