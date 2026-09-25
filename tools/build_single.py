import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "src" / "process_closer"
OUTPUT = ROOT / "dist" / "process_closer.py"
SOURCES = (
    "errors.py",
    "models.py",
    "policy.py",
    "processes.py",
    "monitor.py",
    "application.py",
)


def prepare_source(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("process_closer")
        )
    ]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    source = "\n\n".join(prepare_source(SOURCE_DIR / name) for name in SOURCES)
    OUTPUT.write_text(f"{source}\n\nraise SystemExit(run())\n", encoding="utf-8", newline="\n")
    return OUTPUT


result = build()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
print(f"Готово: {result.relative_to(ROOT)}")
