"""Read single-row INSERT values in local MySQL seed dumps without losing escapes."""
import re
from pathlib import Path


def values(line):
    value, result, quoted, index = [], [], False, 0
    raw = line.strip().rstrip(",;")[1:-1]
    escapes = {"0": "\0", "n": "\n", "r": "\r", "t": "\t", "b": "\b", "Z": "\x1a"}
    while index < len(raw):
        char = raw[index]
        if quoted and char == "\\":
            index += 1
            if index >= len(raw):
                raise ValueError("Truncated SQL escape")
            value.append(escapes.get(raw[index], raw[index]))
        elif char == "'":
            if quoted and index + 1 < len(raw) and raw[index + 1] == "'":
                value.append("'")
                index += 1
            else:
                quoted = not quoted
        elif char == "," and not quoted:
            result.append("".join(value).strip())
            value = []
        else:
            value.append(char)
        index += 1
    if quoted:
        raise ValueError("Unclosed SQL string")
    result.append("".join(value).strip())
    return result


def rows(path: Path, tables=None):
    table, columns = None, []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("INSERT INTO "):
            match = re.match(r"INSERT INTO `([^`]+)` \((.*?)\)", line)
            table = match[1] if match and (tables is None or match[1] in tables) else None
            if table:
                columns = re.findall(r"`([^`]+)`", match[2])
        elif table and line.startswith("("):
            parsed = values(line)
            if len(parsed) != len(columns):
                raise ValueError(f"Wrong column count in {table}")
            yield table, dict(zip(columns, parsed))
