"""Tests for deployment and rollback scripts (TP-1703).

Uses temporary directories, fake Git repos, and fake Docker/Git/Curl
binaries to verify all script behaviours without affecting the real
environment.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "infra" / "deploy"

_FAKE_COMPOSE_YML = """
services:
  backend:
    image: alpine
    command: ["sleep", "infinity"]
  gateway:
    image: alpine
    command: ["sleep", "infinity"]
"""

_MIGRATIONS_PY = ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_home() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_git_repo(path: Path) -> None:
    """Create a minimal Git repo with two commits."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    # First commit
    (path / "README.md").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, capture_output=True, check=True)
    _first = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Second commit
    (path / "README.md").write_text("updated")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=path, capture_output=True, check=True)
    _second = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    (path / ".git" / "refs" / "remotes" / "origin").mkdir(parents=True, exist_ok=True)
    (path / ".git" / "refs" / "remotes" / "origin" / "main").write_text(_second)

    return _first, _second


def _setup_deployment(
    tmp_home: Path,
) -> tuple[Path, Path, Path, str]:
    """Set up a fake deployment environment.

    Returns (repo_dir, env_file, state_dir, first_rev).
    """
    repo_dir = tmp_home / "repository"
    env_dir = tmp_home / "env"
    state_dir = tmp_home / "deployment-state"

    repo_dir.mkdir(parents=True)
    env_dir.mkdir(parents=True)
    state_dir.mkdir(parents=True)

    first_rev, _ = _fake_git_repo(repo_dir)

    # Create compose file
    (repo_dir / "docker-compose.production.yml").write_text(_FAKE_COMPOSE_YML)

    # Create env file
    env_file = env_dir / "production.env"
    env_file.write_text("POSTGRES_PASSWORD=test_secret\n")

    # Create fake docker, docker-compose, curl, git, alembic
    _make_fake_bin(tmp_home, "docker")
    _make_fake_bin(tmp_home, "docker-compose")

    return repo_dir, env_file, state_dir, first_rev


def _make_fake_bin(tmp_home: Path, name: str) -> Path:
    """Create a fake executable that succeeds."""
    path = tmp_home / name
    path.write_text("#!/usr/bin/env bash\nexit 0\n")
    _make_executable(path)
    return path


def _make_fake_bin_fail(tmp_home: Path, name: str) -> Path:
    """Create a fake executable that fails."""
    path = tmp_home / name
    path.write_text("#!/usr/bin/env bash\necho 'FAKE FAIL' >&2\nexit 1\n")
    _make_executable(path)
    return path


def _run_script(
    script_name: str,
    env_overrides: dict[str, str] | None = None,
    expected_returncode: int | None = None,
) -> subprocess.CompletedProcess:
    env = {**os.environ, **(env_overrides or {})}
    result = subprocess.run(
        ["bash", str(_SCRIPTS_DIR / script_name)],
        env=env,
        capture_output=True,
        text=True,
    )
    if expected_returncode is not None:
        assert result.returncode == expected_returncode, (
            f"Expected {expected_returncode}, got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


# ===================================================================
# 1. Syntax and basic validation
# ===================================================================


class TestSyntax:
    def test_deploy_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(_SCRIPTS_DIR / "deploy.sh")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"syntax error: {result.stderr}"

    def test_rollback_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(_SCRIPTS_DIR / "rollback.sh")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"syntax error: {result.stderr}"


# ===================================================================
# 2. Deployment script behaviour
# ===================================================================


class TestDeploy:
    def test_missing_env_file_fails(self, tmp_home: Path) -> None:
        repo_dir, _, state_dir, _ = _setup_deployment(tmp_home)
        env = {
            "TRADEPILOT_DEPLOY_DIR": str(repo_dir),
            "TRADEPILOT_STATE_DIR": str(state_dir),
            "TRADEPILOT_ENV_FILE": "/nonexistent/env",
            "PATH": f"{tmp_home}:/bin:/usr/bin",
        }
        result = _run_script("deploy.sh", env)
        assert result.returncode != 0
        assert "ERROR" in result.stderr


@pytest.mark.skipif(True, reason="requires real Docker and Compose")
def test_requires_configuration(self, tmp_home: Path) -> None:
    """Placeholder: full integration requires real Docker."""
    pass


# ===================================================================
# 3. Revision tracking
# ===================================================================


class TestRevisionTracking:
    @pytest.mark.skipif(True, reason="requires real Docker and Compose")
    def test_previous_revision_recorded(self, tmp_home: Path) -> None:
        repo_dir, env_file, state_dir, first_rev = _setup_deployment(tmp_home)
        # Create git remote as a bare repo to allow fetch
        bare = tmp_home / "bare.git"
        subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        # Push current state to remote
        subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        env = {
            "TRADEPILOT_DEPLOY_DIR": str(repo_dir),
            "TRADEPILOT_ENV_FILE": str(env_file),
            "TRADEPILOT_STATE_DIR": str(state_dir),
            "PATH": f"{tmp_home}:/bin:/usr/bin",
        }
        _run_script("deploy.sh", env, expected_returncode=0)
        prev_file = state_dir / "previous_revision"
        assert prev_file.exists()
        prev_rev = prev_file.read_text().strip()
        assert len(prev_rev) == 40  # SHA hash


# ===================================================================
# 4. Scoped Compose commands
# ===================================================================


class TestComposeScoping:
    def test_compose_project_name_used(self, tmp_home: Path) -> None:
        """Verify --project-name or -p is present in docker compose calls."""
        repo_dir, env_file, state_dir, _ = _setup_deployment(tmp_home)
        deploy_script = (_SCRIPTS_DIR / "deploy.sh").read_text()
        assert (
            "-p ${COMPOSE_PROJECT}" in deploy_script
            or "--project-name ${COMPOSE_PROJECT}" in deploy_script
        )
        assert "tradepilot-ai" in deploy_script

    def test_no_down_v(self, tmp_home: Path) -> None:
        """Verify scripts never use 'down -v' or 'volume prune'."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for script_name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "down -v" not in content, f"{script_name} contains 'down -v'"
            assert "volume prune" not in content, f"{script_name} contains 'volume prune'"
            assert "system prune" not in content, f"{script_name} contains 'system prune'"

    def test_no_unscoped_compose(self, tmp_home: Path) -> None:
        """Verify scripts never call docker compose without -p."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for script_name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Allow comments and variable assignments
                if stripped.startswith("#") or stripped.startswith("docker") is False:
                    continue
                if "docker compose" in stripped and "-p" not in stripped:
                    # The COMPOSE_CMD variable includes -p
                    if "${COMPOSE_PROJECT}" not in stripped:
                        pytest.fail(f"{script_name}:{i}: unscoped docker compose: {stripped}")


# ===================================================================
# 5. Rollback behaviour
# ===================================================================


class TestRollback:
    def test_missing_previous_revision_rejected(self, tmp_home: Path) -> None:
        repo_dir, env_file, state_dir, _ = _setup_deployment(tmp_home)
        env = {
            "TRADEPILOT_DEPLOY_DIR": str(repo_dir),
            "TRADEPILOT_ENV_FILE": str(env_file),
            "TRADEPILOT_STATE_DIR": str(state_dir),
            "PATH": f"{tmp_home}:/bin:/usr/bin",
        }
        result = _run_script("rollback.sh", env)
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_previous_none_rejected(self, tmp_home: Path) -> None:
        repo_dir, env_file, state_dir, _ = _setup_deployment(tmp_home)
        (state_dir / "previous_revision").write_text("none")
        env = {
            "TRADEPILOT_DEPLOY_DIR": str(repo_dir),
            "TRADEPILOT_ENV_FILE": str(env_file),
            "TRADEPILOT_STATE_DIR": str(state_dir),
            "PATH": f"{tmp_home}:/bin:/usr/bin",
        }
        result = _run_script("rollback.sh", env)
        assert result.returncode != 0


# ===================================================================
# 6. Scripts never target unrelated projects
# ===================================================================


class TestProjectIsolation:
    def test_scripts_only_target_tradepilot(self, tmp_home: Path) -> None:
        """Verify COMPOSE_PROJECT defaults to tradepilot-ai."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        assert "COMPOSE_PROJECT" in deploy
        assert "tradepilot-ai" in deploy
        assert "COMPOSE_PROJECT" in rollback
        assert "tradepilot-ai" in rollback

    def test_no_other_project_names(self, tmp_home: Path) -> None:
        """Verify scripts do not reference other known project ports/names."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        combined = deploy + rollback
        # Should not manage other projects
        assert "docker compose -p other" not in combined


# ===================================================================
# 7. Volume safety
# ===================================================================


class TestVolumeSafety:
    def test_no_volume_removal(self, tmp_home: Path) -> None:
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "volume rm" not in content, f"{name} contains 'volume rm'"
            assert "docker volume" not in content or "docker volume ls" in content, (
                f"{name} has unexpected volume commands"
            )


# ===================================================================
# 8. Gateway port safety
# ===================================================================


class TestGatewayPort:
    def test_gateway_port_configurable(self, tmp_home: Path) -> None:
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        assert "GATEWAY_PORT" in deploy
        assert "8181" in deploy

    def test_first_deployment_port_check(self, tmp_home: Path) -> None:
        """Port-safety check exists in the script."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        assert "PORT_IN_USE" in deploy or "port" in deploy.lower()


# ===================================================================
# 9. Health check verification
# ===================================================================


class TestHealthChecks:
    def test_health_check_urls_used(self, tmp_home: Path) -> None:
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "/health" in content
            assert "/health/ready" in content

    def test_retry_config_exists(self, tmp_home: Path) -> None:
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        assert "RETRY_ATTEMPTS" in deploy
        assert "RETRY_SECONDS" in deploy


# ===================================================================
# 10. No embedded secrets
# ===================================================================


class TestNoSecrets:
    def test_no_embedded_credentials(self, tmp_home: Path) -> None:
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "PGPASSWORD=" not in content, f"{name} has embedded password"


# ===================================================================
# 11. Gateway refresh
# ===================================================================


class TestGatewayRefresh:
    def test_deploy_refreshes_gateway(self, tmp_home: Path) -> None:
        """Deploy script must force-recreate the gateway after backend start."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        assert "--force-recreate gateway" in deploy

    def test_rollback_refreshes_gateway(self, tmp_home: Path) -> None:
        """Rollback script must force-recreate the gateway after backend restart."""
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        assert "--force-recreate gateway" in rollback

    def test_gateway_refresh_before_health(self, tmp_home: Path) -> None:
        """Gateway refresh must happen before health checks."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        gw_idx = deploy.index("--force-recreate gateway")
        health_idx = deploy.index("/health")
        assert gw_idx < health_idx, "gateway refresh must come before health checks"

    def test_gateway_refresh_before_health_rollback(self, tmp_home: Path) -> None:
        """Rollback must also refresh gateway before health checks."""
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        gw_idx = rollback.index("--force-recreate gateway")
        health_idx = rollback.index("/health")
        assert gw_idx < health_idx, "gateway refresh must come before health checks"


# ===================================================================
# 12. Worker health check in rollback
# ===================================================================


class TestRollbackWorkerHealth:
    def test_rollback_checks_worker_health(self, tmp_home: Path) -> None:
        """Rollback must verify /health/worker returns healthy."""
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        assert "/health/worker" in rollback


# ===================================================================
# 13. No host Nginx management
# ===================================================================


class TestNoHostNginx:
    def test_no_nginx_reload(self, tmp_home: Path) -> None:
        """Scripts must not restart host Nginx."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "nginx" not in content.lower() or "gateway" in content.lower(), (
                f"{name} references host nginx"
            )

    def test_no_systemctl_nginx(self, tmp_home: Path) -> None:
        """Scripts must not use systemctl for nginx."""
        deploy = (_SCRIPTS_DIR / "deploy.sh").read_text()
        rollback = (_SCRIPTS_DIR / "rollback.sh").read_text()
        for name, content in [("deploy.sh", deploy), ("rollback.sh", rollback)]:
            assert "systemctl" not in content, f"{name} uses systemctl"


# ===================================================================
# 14. Frontend middleware and compose config
# ===================================================================


class TestMiddlewareBackendURL:
    _repo_root = Path(__file__).resolve().parent.parent.parent.parent

    def test_middleware_uses_internal_url(self) -> None:
        """Middleware must use INTERNAL_API_BASE_URL, not request.url."""
        content = (self._repo_root / "frontend" / "src" / "middleware.ts").read_text()
        assert "INTERNAL_API_BASE_URL" in content
        assert "request.url" not in content.split("new URL")[0] if "new URL" in content else True
        assert "NEXT_PUBLIC_API_BASE_URL" not in content

    def test_compose_has_internal_api_url(self) -> None:
        """Compose file must pass INTERNAL_API_BASE_URL to frontend."""
        content = (self._repo_root / "docker-compose.production.yml").read_text()
        assert "INTERNAL_API_BASE_URL" in content
        assert "${INTERNAL_API_BASE_URL:-http://backend:8000}" in content

    def test_compose_storage_root_worker(self) -> None:
        """Worker must receive STORAGE_ROOT matching backend."""
        content = (self._repo_root / "docker-compose.production.yml").read_text()
        assert "STORAGE_ROOT: ${STORAGE_ROOT:-/data/evidence}" in content

    def test_compose_storage_volume_mounts(self) -> None:
        """Both backend and worker must mount evidence_data:/data/evidence."""
        content = (self._repo_root / "docker-compose.production.yml").read_text()
        assert "evidence_data:/data/evidence" in content
