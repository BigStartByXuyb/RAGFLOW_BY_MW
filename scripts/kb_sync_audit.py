#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""Audit a knowledge-base sync batch taken from upstream.

Run this after adopting upstream files into the fork and before committing:

    python scripts/kb_sync_audit.py --lock <upstream uv.lock>

It checks three failure modes that a plain `git merge` review does not catch:

1. syntax errors in the adopted Python files;
2. imports that unchanged fork files make into adopted modules, where the
   imported name no longer exists (renamed/removed helpers);
3. references to the agent / DataFlow surfaces this fork deliberately removed.

The lock file check is optional; without it the third-party dependency report
is skipped.
"""

import argparse
import ast
import os
import re
import subprocess
import sys

# Symbols and modules that belong to the removed canvas-agent / DataFlow
# surfaces. The fork must not re-introduce them through an upstream sync.
REMOVED_PATTERNS = (
    r"rag\.flow\b",
    r"from rag import flow\b",
    r"dataflow_service",
    r"canvas_service",
    r"user_canvas_version",
    r"canvas_replica",
    r"db\.template_utils",
    r"agent_api",
    r"bot_api",
    r"plugin_api",
    r"agent\.canvas",
    r"sandbox_artifact",
)

# Import name -> distribution name, for packages whose import name differs.
IMPORT_ALIASES = {
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "google": "google-api-python-client",
    "infinity": "infinity-sdk",
    "opensearchpy": "opensearch-py",
    "Crypto": "pycryptodome",
    "sentry_sdk": "sentry-sdk",
    "ruamel": "ruamel-yaml",
    "tencentcloud": "tencentcloud-sdk-python",
    "websocket": "websocket-client",
    "multipart": "python-multipart",
    "typing_extensions": "typing-extensions",
    "imageio_ffmpeg": "imageio-ffmpeg",
    "psycopg2": "psycopg2-binary",
    "tavily": "tavily-python",
    "zai": "zai-sdk",
    "elastic_transport": "elastic-transport",
    "atlassian": "atlassian-python-api",
    "azure": "azure-storage-blob",
    "github": "pygithub",
    "moodle": "moodlepy",
    "box_sdk_gen": "boxsdk",
    "pkg_resources": "setuptools",
}

# Imported lazily and intentionally outside the lock file: downloaded by
# `ragflow_deps/download_deps.py` or provided by an optional runtime image.
OPTIONAL_IMPORTS = {"torch", "jina", "ais_bench", "imageio_ffmpeg", "ffmpeg"}

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".playwright-cli", ".playwright-mcp"}

# Only source files are scanned for removed-surface references; this audit
# script itself lists the patterns it looks for.
SCANNED_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".vue")
SCAN_EXCLUDES = {"scripts/kb_sync_audit.py"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, encoding="utf-8", errors="replace").stdout


def working_tree_files() -> set[str]:
    files = set()
    for line in git("status", "--porcelain").splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[1]
        files.add(path.replace("\\", "/"))
    return files


def rev_range_files(rev_range: str) -> set[str]:
    return {f.replace("\\", "/") for f in git("diff", "--name-only", "--diff-filter=d", rev_range).splitlines() if f}


def walk_python() -> list[str]:
    out = []
    for root, dirs, names in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        out.extend(os.path.join(root, n).replace("\\", "/").lstrip("./") for n in names if n.endswith(".py"))
    return out


def module_path(module: str) -> str | None:
    path = module.replace(".", "/")
    for candidate in (f"{path}.py", os.path.join(path, "__init__.py")):
        if os.path.isfile(candidate):
            return candidate
    return None


def module_names(module: str) -> set[str]:
    path = module_path(module)
    if path is None:
        return set()
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(a.asname or a.name.split(".")[0] for a in node.names)
    return names


def has_star_import(module: str) -> bool:
    path = module_path(module)
    if path is None:
        return False
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return False
    return any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(tree))


def check_syntax(files: set[str]) -> list[str]:
    errors = []
    for rel in sorted(f for f in files if f.endswith(".py")):
        if not os.path.isfile(rel):
            continue
        try:
            compile(open(rel, encoding="utf-8", errors="replace").read(), rel, "exec")
        except SyntaxError as exc:
            errors.append(f"{rel}: {exc}")
    return errors


def check_stale_imports(files: set[str]) -> list[str]:
    adopted = {f for f in files if f.endswith(".py")}
    cache: dict[str, set[str]] = {}
    problems = []
    for rel in walk_python():
        if rel in adopted:
            continue
        try:
            tree = ast.parse(open(rel, encoding="utf-8", errors="replace").read())
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module or node.level:
                continue
            target = module_path(node.module)
            if target is None or target.lstrip("./") not in adopted:
                continue
            if has_star_import(node.module):
                continue
            if node.module not in cache:
                cache[node.module] = module_names(node.module)
            base = os.path.dirname(target)
            for name in node.names:
                if name.name == "*" or name.name in cache[node.module]:
                    continue
                if os.path.isfile(os.path.join(base, f"{name.name}.py")) or os.path.isdir(os.path.join(base, name.name)):
                    continue
                problems.append(f"{rel}:{node.lineno}: {node.module} has no '{name.name}'")
    return problems


def check_removed_surfaces(files: set[str]) -> list[str]:
    pattern = re.compile("|".join(REMOVED_PATTERNS))
    hits = []
    for rel in sorted(files):
        if rel in SCAN_EXCLUDES or not rel.endswith(SCANNED_SUFFIXES) or not os.path.isfile(rel):
            continue
        for lineno, line in enumerate(open(rel, encoding="utf-8", errors="replace"), 1):
            if pattern.search(line):
                hits.append(f"{rel}:{lineno}: {line.strip()[:140]}")
    return hits


def check_dependencies(files: set[str], lock_path: str) -> list[str]:
    available = {
        name.lower().replace("_", "-")
        for name in re.findall(r'^name = "([^"]+)"', open(lock_path, encoding="utf-8").read(), re.M)
    }
    local = {d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")}
    stdlib = set(sys.stdlib_module_names)
    missing: dict[str, str] = {}
    for rel in sorted(f for f in files if f.endswith(".py")):
        if not os.path.isfile(rel):
            continue
        try:
            tree = ast.parse(open(rel, encoding="utf-8", errors="replace").read())
        except Exception:
            continue
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                roots.add(node.module.split(".")[0])
        for root in roots:
            if root in local or root in stdlib or root in OPTIONAL_IMPORTS or root.startswith("_"):
                continue
            candidates = {root.lower().replace("_", "-"), root.lower().replace("_", "-") + "-python"}
            if root in IMPORT_ALIASES:
                candidates.add(IMPORT_ALIASES[root].lower().replace("_", "-"))
            if not (candidates & available):
                missing.setdefault(root, rel)
    return [f"{rel}: import '{root}' is not resolvable from the lock file" for root, rel in sorted(missing.items())]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", help="path to the upstream uv.lock for the dependency check")
    parser.add_argument("--range", dest="rev_range", help="audit a commit range (e.g. main..HEAD) instead of the working tree")
    args = parser.parse_args()

    files = rev_range_files(args.rev_range) if args.rev_range else working_tree_files()
    print(f"auditing {len(files)} changed files")

    sections = [
        ("syntax errors", check_syntax(files)),
        ("stale imports into adopted modules", check_stale_imports(files)),
        ("references to removed agent/DataFlow surfaces", check_removed_surfaces(files)),
    ]
    if args.lock:
        sections.append(("unresolved third-party imports", check_dependencies(files, args.lock)))

    failed = False
    for title, problems in sections:
        print(f"\n{title}: {len(problems)}")
        for problem in problems[:40]:
            print(f"  {problem}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
