"""Sample script for PyObfuscation script mode."""

APP_NAME = "PyObfuscation"
EMPTY_TEXT = ""
UNICODE_TEXT = "สวัสดี"


def greet(name="World"):
    """Return a greeting for script obfuscation tests."""
    message = "Hello"
    punctuation = "!"
    return f"{message}, {name}{punctuation}"


def main():
    secret = "this string should be obfuscated"
    print(APP_NAME)
    print(repr(EMPTY_TEXT))
    print(UNICODE_TEXT)
    print(greet())
    print(secret)


if __name__ == "__main__":
    main()
