"""
Import-chain tests: backend modules must load when the process is launched
from the repository root (not only from inside backend/), because config
files are resolved relative to the module location, never the CWD.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_from_root(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("ANTHROPIC_API_KEY", "placeholder-key-for-import-test")
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_agent_engine_imports_from_repo_root():
    proc = _run_from_root(
        "import sys; sys.path.insert(0, 'backend'); "
        "import game_engine, monte_carlo_equity, agent_engine; "
        "print('OK', agent_engine.MC_SIMULATIONS)"
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_llm_agent_imports_from_repo_root():
    proc = _run_from_root(
        "import sys; sys.path.insert(0, 'backend'); "
        "import llm_agent; "
        "print('OK', llm_agent.MC_SIMULATIONS)"
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_main_module_imports_from_repo_root():
    proc = _run_from_root(
        "import sys; sys.path.insert(0, 'backend'); "
        "import main; "
        "print('OK')"
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout
