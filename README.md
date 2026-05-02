# PyObfuscation
 A simple string obfuscation to secure your strings, confuses by using logic gates and true/false directs.

##### Usage
```python3 . <string>```

##### Example
```python3 . "Hello World"```

##### Script mode
```python3 . -i script.py -o out.py```

##### Compile obfuscated script to .pyc
```python3 . -i script.py -o out.py --pyc out.pyc```

Run the bytecode with the same Python version:
```python3 out.pyc```

##### Add source-level jump/control-flow obfuscation
```python3 . -i script.py -o out.py --pyc out.pyc --control-flow```

##### Inspect Python bytecode assembly
```python3 . -i script.py --control-flow --disassemble```

Python bytecode is CPython's stack-machine instruction format. The
`--disassemble` option prints the `dis` module view of the generated code.
With `--control-flow`, the generated source contains opaque `if` and `while`
blocks that compile into jump instructions.
