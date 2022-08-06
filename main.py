import random
import time
import os
import sys

random.seed(int(time.time()))
os.system("cls")


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


def toNum(bin):
    return int(bin, 2)


def obfuscateNumber(num, list):
    num = toBin(num)
    b = list[2]
    a, c = "", ""
    for i, v in enumerate(num):
        pick = list[int(num[i])]
        pick = pick[random.randint(0, len(pick) - 1)]
        a, c = a + pick[0], c + pick[1]
    return ("%s%s%s" % (toHex(int(toNum(a))), b, toHex(int(toNum(c)))))


def obfuscateBoolean(bool):
    eq = ["==", "!=", ">", "<", ">=", "<="]
    a, c = obfuscateNumber(
        random.randint(100, 300), 
        gates[random.randint(0, len(gates) - 1)]), obfuscateNumber(random.randint(100, 300), 
        gates[random.randint(0, len(gates) - 1)]
    )
    while True:
        b = eq[random.randint(0, len(eq) - 1)]
        result = eval("(%s)%s(%s)" % (a, b, c))
        if result == bool:
            break
    return ("(%s)%s(%s)" % (a, b, c))


def obfuscateString(string):
    arr = []
    for i, v in enumerate(string):
        byte = obfuscateNumber(ord(string[i]), gates[random.randint(0, len(gates) - 1)])
        falsebyte = obfuscateNumber(ord(
            string[i]) + random.randint(-10, 10), 
            gates[random.randint(0, len(gates) - 1)]
        )
        boolean = bool(random.randint(0, 1))
        order = [byte, falsebyte] if boolean else [falsebyte, byte]
        arr.append(
            f"(({obfuscateBoolean(boolean)})and(chr({order[0]}))or(chr({order[1]})))"
        )
    return "+".join(arr)


data = obfuscateString(sys.argv[1])
print(data)