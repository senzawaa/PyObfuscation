# PyObfuscation
 A simple string obfuscation to secure your strings, confuses by using logic gates and true/false directs.

##### Usage
```python3 . <string>```

##### Example
```python3 . "Hello World"```

##### Script mode
```python3 . -i script.py -o out.py```

Script mode strips comments/docstrings and obfuscates constants, module
globals, builtin function calls, and local variable names.

##### Compile obfuscated script to .pyc
```python3 . -i script.py -o out.py --pyc out.pyc```

Run the bytecode with the same Python version:
```python3 out.pyc```

##### Add source-level jump/control-flow obfuscation
```python3 . -i script.py -o out.py --control-flow```

The `--control-flow` option rewrites the Python AST so normal statements are
executed through shuffled state-machine loops while preserving runtime
behavior.
