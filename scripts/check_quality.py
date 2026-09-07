"""Measure functions using coverage's attribution and Radon's native complexity."""
import hashlib
import json
from pathlib import Path
import sys

from radon.complexity import cc_visit
from radon.visitors import Function

paths = sorted(Path("tools").glob("*.py")) + sorted(Path("provider").glob("*.py"))
paths.append(Path("scripts/check_package.py"))
sources = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
context = "source:" + hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
if sys.argv[1:] == ["--fingerprint"]:
    print(context)
    raise SystemExit(0)
coverage = json.loads(Path(sys.argv[1]).read_text())["files"]
results = []
for path in paths:
    functions = [block for block in cc_visit(path.read_text()) if isinstance(block, Function)]
    if not functions:
        raise SystemExit(f"No functions measured in {path}")
    file_report = coverage[str(path)]
    entries = file_report["functions"]
    for function in functions:
        name = f"{function.classname}.{function.name}" if function.classname else function.name
        measured = entries[name]
        summary = measured["summary"]
        counts = [summary[key] for key in ("covered_lines", "missing_lines", "num_statements", "excluded_lines")]
        if any(type(count) is not int or count < 0 for count in counts) or counts[2] == 0:
            raise SystemExit(f"Invalid native statement counts: {path}:{name}")
        executed, missing, excluded = (measured[key] for key in ("executed_lines", "missing_lines", "excluded_lines"))
        for lines in (executed, missing, excluded):
            if any(type(line) is not int or line < 1 for line in lines) or len(set(lines)) != len(lines):
                raise SystemExit(f"Invalid native statement lines: {path}:{name}")
        if (counts != [len(executed), len(missing), len(executed) + len(missing), len(excluded)]
                or set(executed) & set(missing) or set(excluded) & (set(executed) | set(missing))):
            raise SystemExit(f"Inconsistent native statement attribution: {path}:{name}")
        if measured["start_line"] != function.lineno:
            raise SystemExit(f"Mismatched function coverage: {path}:{name}")
        contexts = file_report["contexts"]
        if any(context not in contexts.get(str(line), []) for line in executed):
            raise SystemExit(f"Coverage source fingerprint mismatch: {path}:{name}")
        fraction = counts[0] / counts[2]
        complexity = function.complexity
        crap = complexity ** 2 * (1 - fraction) ** 3 + complexity
        results.append({"file": str(path), "function": name, "coverage": fraction,
                        "complexity": complexity, "crap": crap, "source_context": context,
                        "sha256": sources[str(path)]})
        if crap > 30:
            raise SystemExit(f"CRAP exceeds 30: {path}:{name}: {crap}")
if len(results) < 10:
    raise SystemExit("Expected the tool, provider, input, output and package functions")
print(json.dumps(results, indent=2))
