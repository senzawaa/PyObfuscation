import argparse
import ast
import builtins
import dis
import io
import importlib.util
import marshal
import random
import struct
import time
import tokenize

random.seed(int(time.time()))

BUILTIN_GLOBAL_NAMES = {
    name
    for name in dir(builtins)
    if name.isidentifier()
    and not name.startswith("__")
    and callable(getattr(builtins, name))
}


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


def randomConfusingName():
    return f"_0x{random.getrandbits(64):016x}"


class DocstringStripper(ast.NodeTransformer):
    def visit_Module(self, node):
        node.body = self.stripBody(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        node.body = self.stripBody(node.body)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.body = self.stripBody(node.body)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.body = self.stripBody(node.body)
        self.generic_visit(node)
        return node

    def stripBody(self, body):
        if self.hasDocstring(body):
            body = body[1:]
        return body or [ast.Pass()]

    def hasDocstring(self, body):
        return (
            bool(body)
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        )


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


class ModuleGlobalCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def collect(self, body):
        for statement in body:
            self.visit(statement)
        return self.names

    def visit_FunctionDef(self, node):
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node):
        self.names.add(node.name)

    def visit_ClassDef(self, node):
        self.names.add(node.name)

    def visit_Import(self, node):
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_ListComp(self, node):
        return

    def visit_SetComp(self, node):
        return

    def visit_DictComp(self, node):
        return

    def visit_GeneratorExp(self, node):
        return

    def visit_Lambda(self, node):
        return


class FunctionLocalCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()
        self.globalNames = set()
        self.nonlocalNames = set()

    def collect(self, node):
        self.collectArguments(node.args)
        for statement in node.body:
            self.visit(statement)
        return self.names - self.globalNames - self.nonlocalNames

    def collectArguments(self, args):
        for arg in (
            args.posonlyargs
            + args.args
            + args.kwonlyargs
        ):
            self.names.add(arg.arg)
        if args.vararg:
            self.names.add(args.vararg.arg)
        if args.kwarg:
            self.names.add(args.kwarg.arg)

    def visit_Global(self, node):
        self.globalNames.update(node.names)

    def visit_Nonlocal(self, node):
        self.nonlocalNames.update(node.names)

    def visit_FunctionDef(self, node):
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node):
        self.names.add(node.name)

    def visit_ClassDef(self, node):
        self.names.add(node.name)

    def visit_Import(self, node):
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.names.add(node.name)
        for statement in node.body:
            self.visit(statement)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_ListComp(self, node):
        return

    def visit_SetComp(self, node):
        return

    def visit_DictComp(self, node):
        return

    def visit_GeneratorExp(self, node):
        return

    def visit_Lambda(self, node):
        return


class NameObfuscator(ast.NodeTransformer):
    def __init__(self):
        self.moduleGlobals = set()
        self.globalAlias = None
        self.builtinAlias = None
        self.localScopes = []
        self.classDepth = 0
        self.usedNames = set()
        super().__init__()

    def visit_Module(self, node):
        self.moduleGlobals = ModuleGlobalCollector().collect(node.body)
        self.usedNames = set(self.moduleGlobals)
        self.builtinAlias = self.uniqueName()
        if self.moduleGlobals:
            self.globalAlias = self.uniqueName()

        headerLength = self.moduleHeaderLength(node.body)
        header = node.body[:headerLength]
        body = self.visitStatementList(node.body[headerLength:])
        if self.globalAlias:
            body.insert(0, self.globalAliasAssignment())
        if self.builtinAlias:
            body.insert(0, self.builtinAliasAssignment())
        node.body = header + body
        return node

    def moduleHeaderLength(self, body):
        headerLength = 1 if self.hasDocstring(body) else 0
        while (
            headerLength < len(body)
            and isinstance(body[headerLength], ast.ImportFrom)
            and body[headerLength].module == "__future__"
        ):
            headerLength += 1
        return headerLength

    def visitStatementList(self, body):
        result = []
        for statement in body:
            transformed = self.visit(statement)
            if isinstance(transformed, list):
                result.extend(transformed)
            elif transformed is not None:
                result.append(transformed)
        return result

    def visit_FunctionDef(self, node):
        if self.isModuleScope():
            return self.visitModuleFunction(node)
        self.renameLocalBinding(node)
        self.visitFunctionOuterParts(node)
        self.visitFunctionBody(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        if self.isModuleScope():
            return self.visitModuleFunction(node)
        self.renameLocalBinding(node)
        self.visitFunctionOuterParts(node)
        self.visitFunctionBody(node)
        return node

    def visitModuleFunction(self, node):
        originalName = node.name
        temporaryName = self.uniqueName()
        node.name = temporaryName
        self.visitFunctionOuterParts(node)
        self.visitFunctionBody(node)
        return [
            node,
            self.exportGlobal(originalName, temporaryName),
            self.deleteName(temporaryName),
        ]

    def visitFunctionOuterParts(self, node):
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        self.visitArgumentOuterParts(node.args)
        if node.returns:
            node.returns = self.visit(node.returns)

    def visitArgumentOuterParts(self, args):
        for defaultIndex, default in enumerate(args.defaults):
            args.defaults[defaultIndex] = self.visit(default)
        for defaultIndex, default in enumerate(args.kw_defaults):
            if default is not None:
                args.kw_defaults[defaultIndex] = self.visit(default)
        for arg in self.iterArguments(args):
            if arg.annotation:
                arg.annotation = self.visit(arg.annotation)

    def visitFunctionBody(self, node):
        localMap = self.localRenameMap(node)
        self.renameArguments(node.args, localMap)
        self.localScopes.append(localMap)
        node.body = self.visitStatementList(node.body)
        self.localScopes.pop()

    def localRenameMap(self, node):
        return {
            name: self.uniqueName()
            for name in sorted(FunctionLocalCollector().collect(node))
        }

    def renameArguments(self, args, localMap):
        for arg in self.iterArguments(args):
            if arg.arg in localMap:
                arg.arg = localMap[arg.arg]

    def iterArguments(self, args):
        arguments = args.posonlyargs + args.args + args.kwonlyargs
        if args.vararg:
            arguments.append(args.vararg)
        if args.kwarg:
            arguments.append(args.kwarg)
        return arguments

    def visit_ClassDef(self, node):
        if self.isModuleScope():
            return self.visitModuleClass(node)
        self.renameLocalBinding(node)
        self.visitClassOuterParts(node)
        return node

    def visitModuleClass(self, node):
        originalName = node.name
        temporaryName = self.uniqueName()
        node.name = temporaryName
        self.visitClassOuterParts(node)
        return [
            node,
            self.exportGlobal(originalName, temporaryName),
            self.deleteName(temporaryName),
        ]

    def visitClassOuterParts(self, node):
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        node.bases = [self.visit(item) for item in node.bases]
        node.keywords = [self.visit(item) for item in node.keywords]

    def visit_Import(self, node):
        if self.localScopes:
            for alias in node.names:
                boundName = alias.asname or alias.name.split(".")[0]
                localName = self.lookupLocal(boundName)
                if localName:
                    alias.asname = localName
        return node

    def visit_ImportFrom(self, node):
        if self.localScopes:
            for alias in node.names:
                if alias.name == "*":
                    continue
                boundName = alias.asname or alias.name
                localName = self.lookupLocal(boundName)
                if localName:
                    alias.asname = localName
        return node

    def visit_ExceptHandler(self, node):
        if node.type:
            node.type = self.visit(node.type)
        if node.name:
            localName = self.lookupLocal(node.name)
            if localName:
                node.name = localName
        node.body = self.visitStatementList(node.body)
        return node

    def visit_Nonlocal(self, node):
        node.names = [self.lookupOuterLocal(name) or name for name in node.names]
        return node

    def visit_ListComp(self, node):
        return node

    def visit_SetComp(self, node):
        return node

    def visit_DictComp(self, node):
        return node

    def visit_GeneratorExp(self, node):
        return node

    def visit_Lambda(self, node):
        return node

    def visit_Name(self, node):
        localName = self.lookupLocal(node.id)
        if localName:
            return ast.copy_location(ast.Name(id=localName, ctx=node.ctx), node)
        if self.globalAlias and node.id in self.moduleGlobals:
            return ast.copy_location(self.globalAccess(node.id, node.ctx), node)
        if (
            self.builtinAlias
            and isinstance(node.ctx, ast.Load)
            and node.id in BUILTIN_GLOBAL_NAMES
        ):
            return ast.copy_location(self.builtinAccess(node.id, node.ctx), node)
        return node

    def renameLocalBinding(self, node):
        localName = self.lookupLocal(node.name)
        if localName:
            node.name = localName

    def isModuleScope(self):
        return not self.localScopes and self.classDepth == 0

    def lookupLocal(self, name):
        for scope in reversed(self.localScopes):
            if name in scope:
                return scope[name]
        return None

    def lookupOuterLocal(self, name):
        for scope in reversed(self.localScopes[:-1]):
            if name in scope:
                return scope[name]
        return None

    def globalAccess(self, name, context):
        return ast.Subscript(
            value=ast.Call(
                func=ast.Name(id=self.globalAlias, ctx=ast.Load()),
                args=[],
                keywords=[],
            ),
            slice=ast.Constant(value=name),
            ctx=context,
        )

    def builtinAccess(self, name, context):
        return ast.Subscript(
            value=ast.Name(id=self.builtinAlias, ctx=ast.Load()),
            slice=ast.Constant(value=name),
            ctx=context,
        )

    def exportGlobal(self, originalName, temporaryName):
        return ast.Assign(
            targets=[self.globalAccess(originalName, ast.Store())],
            value=ast.Name(id=temporaryName, ctx=ast.Load()),
        )

    def deleteName(self, name):
        return ast.Delete(targets=[ast.Name(id=name, ctx=ast.Del())])

    def globalAliasAssignment(self):
        return ast.Assign(
            targets=[ast.Name(id=self.globalAlias, ctx=ast.Store())],
            value=self.builtinAccess("globals", ast.Load()),
        )

    def builtinAliasAssignment(self):
        return ast.Assign(
            targets=[ast.Name(id=self.builtinAlias, ctx=ast.Store())],
            value=ast.IfExp(
                test=ast.Call(
                    func=ast.Name(id="hasattr", ctx=ast.Load()),
                    args=[
                        ast.Name(id="__builtins__", ctx=ast.Load()),
                        ast.Constant(value="__dict__"),
                    ],
                    keywords=[],
                ),
                body=ast.Attribute(
                    value=ast.Name(id="__builtins__", ctx=ast.Load()),
                    attr="__dict__",
                    ctx=ast.Load(),
                ),
                orelse=ast.Name(id="__builtins__", ctx=ast.Load()),
            ),
        )

    def uniqueName(self):
        name = randomConfusingName()
        while name in self.usedNames:
            name = randomConfusingName()
        self.usedNames.add(name)
        return name

    def hasDocstring(self, body):
        return (
            bool(body)
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        )


class ControlFlowObfuscator(ast.NodeTransformer):
    def __init__(self, aggressive=False):
        self.integerObfuscator = ConstantObfuscator(aggressive)
        super().__init__()

    def visit_Module(self, node):
        node.body = self.visitModuleBody(node.body)
        return node

    def visit_FunctionDef(self, node):
        node.body = self.visitBody(node.body, preserveDocstring=True)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.body = self.visitBody(node.body, preserveDocstring=True)
        return node

    def visit_ClassDef(self, node):
        node.body = self.visitBody(node.body, preserveDocstring=True)
        return node

    def visit_If(self, node):
        node.body = self.visitBody(node.body)
        node.orelse = self.visitBody(node.orelse)
        return node

    def visit_For(self, node):
        node.body = self.visitBody(node.body)
        node.orelse = self.visitBody(node.orelse)
        return node

    def visit_AsyncFor(self, node):
        node.body = self.visitBody(node.body)
        node.orelse = self.visitBody(node.orelse)
        return node

    def visit_While(self, node):
        node.body = self.visitBody(node.body)
        node.orelse = self.visitBody(node.orelse)
        return node

    def visit_With(self, node):
        node.body = self.visitBody(node.body)
        return node

    def visit_AsyncWith(self, node):
        node.body = self.visitBody(node.body)
        return node

    def visit_Try(self, node):
        node.body = self.visitBody(node.body)
        node.orelse = self.visitBody(node.orelse)
        node.finalbody = self.visitBody(node.finalbody)
        for handler in node.handlers:
            handler.body = self.visitBody(handler.body)
        return node

    def visit_Match(self, node):
        for case in node.cases:
            case.body = self.visitBody(case.body)
        return node

    def visitModuleBody(self, body):
        headerLength = 1 if self.hasDocstring(body) else 0
        while (
            headerLength < len(body)
            and isinstance(body[headerLength], ast.ImportFrom)
            and body[headerLength].module == "__future__"
        ):
            headerLength += 1
        return body[:headerLength] + self.visitBody(body[headerLength:])

    def visitBody(self, body, preserveDocstring=False):
        headerLength = 1 if preserveDocstring and self.hasDocstring(body) else 0
        while (
            headerLength < len(body)
            and isinstance(body[headerLength], (ast.Global, ast.Nonlocal))
        ):
            headerLength += 1
        header = body[:headerLength]
        body = body[headerLength:]
        visited = []
        for statement in body:
            result = self.visit(statement)
            if isinstance(result, list):
                visited.extend(result)
            elif result is not None:
                visited.append(result)
        return header + self.flattenBody(visited)

    def flattenBody(self, body):
        if not body or not self.canFlatten(body):
            return body

        stateName = self.randomStateName()
        states = self.randomStates(len(body))
        cases = []
        for i, statement in enumerate(body):
            caseBody = [statement]
            if i + 1 < len(body):
                caseBody.append(self.assignState(stateName, states[i + 1]))
            else:
                caseBody.append(ast.Break())
            cases.append((states[i], caseBody))

        cases.extend(self.decoyCases(stateName, states))
        random.shuffle(cases)

        return [
            self.assignState(stateName, states[0]),
            ast.While(
                test=self.opaqueBoolean(True),
                body=[self.caseChain(stateName, cases)],
                orelse=[],
            ),
            self.deleteState(stateName),
        ]

    def canFlatten(self, body):
        if any(
            isinstance(statement, (ast.Global, ast.Nonlocal, ast.Pass))
            for statement in body
        ):
            return False
        return not self.hasFreeLoopControl(body)

    def hasFreeLoopControl(self, body):
        finder = FreeLoopControlFinder()
        for statement in body:
            finder.visit(statement)
            if finder.found:
                return True
        return False

    def randomStateName(self):
        return randomConfusingName()

    def randomStates(self, count):
        states = set()
        while len(states) < count:
            states.add(random.randint(100000, 999999999))
        return list(states)

    def assignState(self, stateName, value):
        return ast.Assign(
            targets=[ast.Name(id=stateName, ctx=ast.Store())],
            value=self.obfuscatedInteger(value),
        )

    def deleteState(self, stateName):
        return ast.Delete(targets=[ast.Name(id=stateName, ctx=ast.Del())])

    def decoyCases(self, stateName, realStates):
        decoys = []
        for _ in range(random.randint(1, max(1, min(3, len(realStates))))):
            decoyState = random.randint(100000, 999999999)
            while decoyState in realStates:
                decoyState = random.randint(100000, 999999999)
            decoys.append((
                decoyState,
                [
                    ast.If(
                        test=self.opaqueBoolean(False),
                        body=[self.assignState(stateName, random.choice(realStates))],
                        orelse=[ast.Pass()],
                    ),
                    ast.Break(),
                ],
            ))
        return decoys

    def caseChain(self, stateName, cases):
        orelse = [ast.Break()]
        for state, body in reversed(cases):
            orelse = [
                ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=stateName, ctx=ast.Load()),
                        ops=[ast.Eq()],
                        comparators=[self.obfuscatedInteger(state)],
                    ),
                    body=body,
                    orelse=orelse,
                )
            ]
        return orelse[0]

    def opaqueBoolean(self, value):
        return ast.parse(obfuscateRuntimeBoolean(value), mode="eval").body

    def obfuscatedInteger(self, value):
        return self.integerObfuscator.obfuscateIntegerValue(value)

    def hasDocstring(self, body):
        return (
            bool(body)
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        )


class FreeLoopControlFinder(ast.NodeVisitor):
    def __init__(self):
        self.found = False

    def visit_Break(self, node):
        self.found = True

    def visit_Continue(self, node):
        self.found = True

    def visit_FunctionDef(self, node):
        return

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_ClassDef(self, node):
        return

    def visit_For(self, node):
        for statement in node.orelse:
            self.visit(statement)

    def visit_AsyncFor(self, node):
        for statement in node.orelse:
            self.visit(statement)

    def visit_While(self, node):
        for statement in node.orelse:
            self.visit(statement)


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


def obfuscateScriptCode(inputPath, aggressive, controlFlow=False):
    with open(inputPath, "r", encoding="utf-8") as source:
        tree = ast.parse(source.read(), filename=inputPath)

    tree = DocstringStripper().visit(tree)
    tree = NameObfuscator().visit(tree)
    tree = ConstantObfuscator(aggressive).visit(tree)
    if controlFlow:
        tree = ControlFlowObfuscator(aggressive).visit(tree)
    ast.fix_missing_locations(tree)
    return minifyPythonWhitespace(ast.unparse(tree)) + "\n"


def obfuscateScript(inputPath, outputPath, aggressive, controlFlow=False):
    writeTextFile(outputPath, obfuscateScriptCode(inputPath, aggressive, controlFlow))


def writeTextFile(path, text):
    with open(path, "w", encoding="utf-8") as target:
        target.write(text)


def compilePyc(sourceCode, pycPath, sourceName):
    code = compile(sourceCode, sourceName, "exec")
    sourceSize = len(sourceCode.encode("utf-8")) & 0xFFFFFFFF
    timestamp = int(time.time()) & 0xFFFFFFFF
    header = importlib.util.MAGIC_NUMBER + struct.pack(
        "<III",
        0,
        timestamp,
        sourceSize,
    )

    with open(pycPath, "wb") as target:
        target.write(header)
        marshal.dump(code, target)


def disassembleSource(sourceCode, sourceName, mode="exec"):
    dis.dis(compile(sourceCode, sourceName, mode))


def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate strings or Python script constants."
    )
    parser.add_argument("string", nargs="?", help="string to obfuscate")
    parser.add_argument("-i", "--input", help="Python script to obfuscate")
    parser.add_argument("-o", "--output", help="where to write the obfuscated script")
    parser.add_argument("--pyc", help="where to write compiled .pyc bytecode")
    parser.add_argument(
        "--disassemble",
        action="store_true",
        help="print Python bytecode disassembly for the generated code",
    )
    parser.add_argument(
        "--control-flow",
        "--jmp",
        dest="control_flow",
        action="store_true",
        help="flatten source bodies into shuffled state-machine loops",
    )
    parser.add_argument(
        "-a",
        "--aggressive",
        action="store_true",
        help="use heavier XOR, runtime noise, and decoy branches",
    )
    args = parser.parse_args()

    if args.input or args.output or args.pyc or args.control_flow:
        if args.string:
            parser.error(
                "string mode cannot be combined with --input/--output/--pyc/--control-flow"
            )
        if not args.input:
            parser.error("--input is required when using --output, --pyc, or --control-flow")
        if not args.output and not args.pyc and not args.disassemble:
            parser.error("use --output, --pyc, or --disassemble with --input")

        sourceCode = obfuscateScriptCode(args.input, args.aggressive, args.control_flow)
        sourceName = args.output or args.pyc or args.input

        if args.output:
            writeTextFile(args.output, sourceCode)
        if args.pyc:
            compilePyc(sourceCode, args.pyc, sourceName)
        if args.disassemble:
            disassembleSource(sourceCode, sourceName)
        return

    if args.string is None:
        parser.error("provide a string or use --input with --output, --pyc, or --disassemble")

    data = (
        obfuscateAggressiveString(args.string)
        if args.aggressive
        else obfuscateString(args.string)
    )
    print(data)
    if args.disassemble:
        print()
        disassembleSource(data, "<obfuscated-string>", mode="eval")


if __name__ == "__main__":
    main()
