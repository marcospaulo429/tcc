"""Isolated file sandbox that runs pytest against agent-written solutions."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_CACHE_DIRS = ("__pycache__", ".pytest_cache")
_SUMMARY_RE = re.compile(r"(\d+)\s+(passed|failed|errors?)")
_TIME_RE = re.compile(r"\bin \d+\.\d+s\b")


def _sanitize(output: str, sandbox_dir: Path) -> str:
    """Remove fontes de não-determinismo (tempo de execução, path aleatório do tempdir)
    antes que a saída entre no contexto do LLM — senão o replay diverge por artefato."""
    output = output.replace(str(sandbox_dir), "<sandbox>")
    return _TIME_RE.sub("", output)


class Sandbox:
    def __init__(self, base_dir: str | Path | None = None):
        if base_dir is None:
            self.dir = Path(tempfile.mkdtemp(prefix="sandbox_"))
        else:
            self.dir = Path(base_dir)
            self.dir.mkdir(parents=True, exist_ok=True)

    def write_file(self, relpath: str, content: str) -> None:
        path = self.dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_file(self, relpath: str) -> str:
        return (self.dir / relpath).read_text(encoding="utf-8")

    def list_files(self) -> list[str]:
        files = []
        for path in self.dir.rglob("*"):
            if path.is_file() and not any(part in _CACHE_DIRS for part in path.parts):
                files.append(path.relative_to(self.dir).as_posix())
        return sorted(files)

    def snapshot(self) -> dict[str, str]:
        return {relpath: self.read_file(relpath) for relpath in self.list_files()}

    def restore(self, snapshot: dict[str, str]) -> None:
        for relpath in self.list_files():
            if relpath not in snapshot:
                (self.dir / relpath).unlink()
        for relpath, content in snapshot.items():
            self.write_file(relpath, content)
        # drop directories left empty after deletions
        for path in sorted((p for p in self.dir.rglob("*") if p.is_dir()), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass

    def run_tests(self, test_code: str, timeout: float = 20.0) -> dict:
        test_path = self.dir / "test_solution.py"
        test_path.write_text(test_code, encoding="utf-8")
        cmd = [
            sys.executable, "-m", "pytest", "test_solution.py",
            "-q", "--tb=line", "-p", "no:cacheprovider",
        ]
        env = {"PATH": os.environ.get("PATH", ""),
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        timed_out = False
        try:
            proc = subprocess.run(
                cmd, cwd=self.dir, env=env, capture_output=True,
                text=True, timeout=timeout,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            parts = []
            for stream in (exc.stdout, exc.stderr):
                if stream:
                    parts.append(stream.decode("utf-8", "replace") if isinstance(stream, bytes) else stream)
            output = "".join(parts) + f"\n[timed out after {timeout}s]"
        finally:
            test_path.unlink(missing_ok=True)
            for path in list(self.dir.rglob("*")):
                if path.is_dir() and path.name in _CACHE_DIRS:
                    shutil.rmtree(path, ignore_errors=True)

        passed = failed = errors = 0
        if not timed_out:
            summary_line = ""
            for line in output.splitlines():
                if _SUMMARY_RE.search(line):
                    summary_line = line
            for match in _SUMMARY_RE.finditer(summary_line):
                count, kind = int(match.group(1)), match.group(2)
                if kind == "passed":
                    passed = count
                elif kind == "failed":
                    failed = count
                else:
                    errors = count

        total = passed + failed + errors
        reward = passed / total if total > 0 else 0.0
        return {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total": total,
            "reward": reward,
            "success": reward == 1.0,
            "output": _sanitize(output, self.dir)[-2000:],
            "timed_out": timed_out,
        }

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)
