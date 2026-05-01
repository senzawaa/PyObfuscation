import argparse
import random
import time

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
        falsebyte = obfuscateNumber(ord(
            string[i]) + random.randint(-10, 10),
            randomGate()
        )
        boolean = bool(random.randint(0, 1))
        order = [byte, falsebyte] if boolean else [falsebyte, byte]
        arr.append(
            f"(({obfuscateBoolean(boolean)})and(chr({order[0]}))or(chr({order[1]})))"
        )
    return "+".join(arr)


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


def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate a string as a Python expression."
    )
    parser.add_argument("string", help="string to obfuscate")
    parser.add_argument(
        "-a",
        "--aggressive",
        action="store_true",
        help="use heavier XOR, runtime noise, and decoy branches",
    )
    args = parser.parse_args()
    data = (
        obfuscateAggressiveString(args.string)
        if args.aggressive
        else obfuscateString(args.string)
    )
    print(data)


if __name__ == "__main__":
    main()
