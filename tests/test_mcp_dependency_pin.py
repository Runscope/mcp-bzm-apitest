"""
Regression guard for the mcp SDK dependency pin (MOB-52688).

Background: mcp-bzm-apim declared its mcp[cli] dependency as ">=1.19.0" with
no upper bound. When the mcp SDK published 2.0, fresh installs (PAG, pip,
uv sync without a lockfile, Docker, PyInstaller) resolved mcp to 2.0.x, and
the 2.0 release moved/removed the mcp.server.fastmcp module, breaking every
import site with ModuleNotFoundError: No module named 'mcp.server.fastmcp'.

These tests import the REAL installed mcp package. Per spec.md's Test
Validity Strategy (Mock-Reality rule), the mcp import must never be mocked
here -- mocking it would hide the exact regression this guard exists to
catch. Do not add unittest.mock.patch around any `mcp` or `mcp.server.*`
import in this file.
"""

import importlib.metadata
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def _installed_mcp_major_version() -> int:
    """Read the installed mcp package version via importlib.metadata.

    Deliberately does not rely on `mcp.__version__` -- that attribute does
    not exist on the mcp distribution (verified against both the 1.x and
    2.x lines), so any guard built on it would silently no-op.
    """
    version_string = importlib.metadata.version("mcp")
    return int(version_string.split(".")[0])


def _major_version_from_string(version_string: str) -> int:
    """Same major-version extraction logic, applied to an arbitrary string.

    Used to exercise the predicate against a simulated version without
    installing a different mcp package (Mock-Reality rule: we do not mock
    the mcp import; we DO simulate a bare version string through the same
    parsing logic used against the real installed package above).
    """
    return int(version_string.split(".")[0])


class TestMcpVersionCap:
    """Covers T002. US1 AC1, US2 AC1/AC2, FR-001, FR-002, SC-001.

    Scenario S1 (positive): the REAL installed mcp package must resolve to
    the 1.x line. Scenario S2 (negative / assumption-challenge): the same
    major-version predicate must reject a simulated 2.x version string --
    proving the guard would have caught the reported regression.
    """

    def test_mcp_version_is_1x(self):
        """Covers T002. Scenario S1 (positive): installed mcp major version == 1.

        This is the guard mandated by FR-005 / SC-001. It asserts against the
        REAL installed `mcp` distribution (no mock). Today, with the unbounded
        pyproject.toml pin, a fresh install resolves mcp to 2.0.x, so this
        test is expected to FAIL until T004 (pyproject.toml cap) lands and the
        environment is reinstalled from the fixed spec.
        """
        installed_version = importlib.metadata.version("mcp")
        major = _installed_mcp_major_version()
        assert major == 1, (
            f"mcp SDK dependency cap violated: installed mcp version is "
            f"'{installed_version}' (major={major}), expected the 1.x line "
            f"(major == 1). A fresh install resolved mcp 2.0+, which removed "
            f"the mcp.server.fastmcp import surface this server depends on. "
            f"Fix: pin 'mcp[cli]' in pyproject.toml to '>=1.19.0,<2' (FR-001)."
        )

    @pytest.mark.parametrize(
        "simulated_version,expected_major",
        [
            ("2.0.0", 2),
            ("2.1.3", 2),
        ],
    )
    def test_version_predicate_rejects_2x(self, simulated_version, expected_major):
        """Covers T002. Scenario S2 (negative / assumption-challenge).

        Proves the major-version predicate used by test_mcp_version_is_1x
        would correctly flag a hypothetical mcp 2.x install as a cap
        violation. This does NOT install mcp 2.x -- it exercises the same
        parsing logic against a literal simulated version string, per
        spec.md's Test Validity Strategy (assumption-challenge case).
        """
        major = _major_version_from_string(simulated_version)
        assert major == expected_major
        # The guard's pass condition (major == 1) must be False for every
        # 2.x version string -- i.e. the guard would have failed loudly
        # instead of allowing a silent broken install.
        assert not (major == 1), (
            f"Version predicate did not reject simulated 2.x version "
            f"'{simulated_version}': the guard would have missed the "
            f"reported regression."
        )


class TestFastmcpImportSurface:
    """Covers T003. US1 AC2, US2 AC1/AC2, FR-003, FR-005, SC-002.

    This is the exact reported regression: under mcp 2.x,
    `from mcp.server.fastmcp import FastMCP, Icon` raises
    ModuleNotFoundError: No module named 'mcp.server.fastmcp'.
    """

    def test_fastmcp_import_surface(self):
        """Covers T003. Scenario S3 (positive / assumption-challenge).

        Imports the REAL mcp.server.fastmcp module (no mock -- Mock-Reality
        rule) and asserts FastMCP is usable as the server class and Context
        is usable as a type. Today, with mcp resolved to 2.0.x, this import
        raises ModuleNotFoundError, so this test is expected to FAIL until
        T004 lands and the environment is reinstalled from the fixed pin.
        """
        try:
            from mcp.server.fastmcp import Context, FastMCP
        except ModuleNotFoundError as exc:
            pytest.fail(
                f"mcp.server.fastmcp import surface is broken: {exc}. "
                f"This is the exact MOB-52688 regression -- a new install "
                f"resolved mcp to a version that removed this module. "
                f"Fix: cap 'mcp[cli]' to '>=1.19.0,<2' in pyproject.toml "
                f"(FR-003, FR-005)."
            )
        assert isinstance(FastMCP, type), "FastMCP must be usable as a class"
        assert Context is not None, "Context must be importable as a usable type"

    def test_icon_symbol_not_imported(self):
        """Covers T003. Scenario S4 (negative / negative-constraint).

        spec.md's Negative Constraints explicitly forbid adding an `Icon`
        import: it appears in the ticket's traceback example but is not used
        anywhere in this repo, and must not be introduced as part of this
        fix. Scans main.py and every tool manager for an accidental
        `from mcp.server.fastmcp import ... Icon ...` import.
        """
        search_paths = [REPO_ROOT / "main.py"] + sorted((REPO_ROOT / "src" / "tools").glob("*.py"))
        icon_import_pattern = re.compile(r"from\s+mcp\.server\.fastmcp\s+import\s+.*\bIcon\b")
        offending_files = []
        for path in search_paths:
            if not path.exists():
                continue
            text = path.read_text()
            if icon_import_pattern.search(text):
                offending_files.append(str(path.relative_to(REPO_ROOT)))
        assert offending_files == [], (
            f"Found forbidden 'Icon' import from mcp.server.fastmcp in: "
            f"{offending_files}. spec.md Negative Constraints: do NOT add "
            f"an Icon import; it is named in the ticket traceback but is "
            f"not used by this repo."
        )


class TestPyprojectPinIsCapped:
    """Covers T004. US1 AC1, FR-001, FR-002, SC-001.

    Static-contract check on the fix itself: the mcp[cli] dependency
    specifier in pyproject.toml must carry an explicit upper bound that
    excludes 2.0 and later. Reads the checked-in pyproject.toml directly --
    no live install or network resolution involved.
    """

    def test_mcp_dependency_has_upper_bound_below_2(self):
        """Covers T004. Scenario S6 (contract / static).

        Parses the `dependencies` array in pyproject.toml and asserts the
        `mcp[cli]` entry carries an explicit `<2` (or equivalent `<2.0.0`)
        upper bound. Today the pin is unbounded ("mcp[cli]>=1.19.0"), so
        this test is expected to FAIL until T004 lands.
        """
        import tomllib

        pyproject_path = REPO_ROOT / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        dependencies = data["project"]["dependencies"]
        mcp_specs = [
            dep
            for dep in dependencies
            if dep.startswith("mcp[")
            or dep.startswith("mcp ")
            or dep == "mcp"
            or dep.startswith("mcp>=")
            or dep.startswith("mcp==")
        ]
        assert mcp_specs, (
            f"Could not find an 'mcp' dependency entry in pyproject.toml " f"dependencies: {dependencies}"
        )
        mcp_spec = mcp_specs[0]
        upper_bound_pattern = re.compile(r"<\s*2(\.0(\.0)?)?(?!\d)")
        assert upper_bound_pattern.search(mcp_spec), (
            f"mcp dependency spec '{mcp_spec}' in pyproject.toml has no "
            f"upper bound excluding 2.0+. Fresh installs (no lockfile) can "
            f"resolve mcp to 2.x, which removes mcp.server.fastmcp and "
            f"breaks every import site (FR-001). Fix: change to "
            f"'mcp[cli]>=1.19.0,<2'."
        )


class TestNoProductionBehaviorChange:
    """Covers T007. FR-004, SC-005.

    Scope-guard: this fix's only production-code change must be the
    dependency specifier (pyproject.toml / uv.lock). No runtime logic, tool
    handler behavior, API-client behavior, or public interface may change.
    Spec-kit planning artifacts under specs/ and the repo's CLAUDE.md guide
    doc are explicitly out of scope for this check -- they are documentation
    committed by the planning stage, not production behavior.
    """

    def test_no_production_behavior_change(self):
        """Covers T007. Scenario S7 (edge / scope-guard).

        Diffs the working tree against the branch's merge-base with its
        default branch and asserts no changed path falls under a production
        source directory (src/, main.py, Dockerfile, build.py, or any other
        top-level Python module) -- only pyproject.toml, uv.lock, tests/,
        specs/, and CLAUDE.md may change. Today (before T004 lands) this
        test is expected to PASS, since no production or dependency file has
        been touched yet; it exists to catch scope creep once the pin fix
        and any accompanying commits land, and is exercised now to confirm
        it evaluates cleanly against the current branch state.

        Skipped gracefully (not failed) if git history/base ref is
        unavailable in this environment, since it depends on repo state
        outside this test's control.
        """
        import subprocess

        allowed_prefixes = ("tests/", "specs/")
        allowed_exact = {"pyproject.toml", "uv.lock", "CLAUDE.md"}

        try:
            base_ref = subprocess.run(
                ["git", "merge-base", "HEAD", "origin/master"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if base_ref.returncode != 0 or not base_ref.stdout.strip():
                base_ref = subprocess.run(
                    ["git", "merge-base", "HEAD", "master"],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            if base_ref.returncode != 0 or not base_ref.stdout.strip():
                pytest.skip("Could not resolve a base ref for the scope-guard diff")
            base_sha = base_ref.stdout.strip()

            diff = subprocess.run(
                ["git", "diff", "--name-only", base_sha, "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pytest.skip("git is unavailable in this environment")

        if diff.returncode != 0:
            pytest.skip("Could not compute scope-guard diff")

        changed_paths = [p for p in diff.stdout.splitlines() if p.strip()]
        disallowed = [
            p for p in changed_paths if p not in allowed_exact and not p.startswith(allowed_prefixes)
        ]
        assert disallowed == [], (
            f"Scope-guard violation: changed files outside "
            f"pyproject.toml/uv.lock/tests//specs//CLAUDE.md: {disallowed}. "
            f"This fix must only change the mcp dependency pin, tests, and "
            f"spec-kit planning artifacts -- no production source file may "
            f"change (FR-004, SC-005)."
        )


class TestLockfileSpecifierHasUpperBound:
    """Covers T006. FR-006.

    Static-contract check: uv.lock's recorded requires-dist specifier for
    `mcp` must carry the same upper bound as pyproject.toml. FR-006 requires
    the lockfile to remain consistent with the new constraint -- if the
    specifier text drifts from pyproject.toml (e.g. lockfile not
    regenerated after a manual pyproject.toml edit review), a future
    `uv sync --locked` or CI lockfile-check could re-resolve without the
    cap. Reads the checked-in uv.lock directly -- no network resolution.
    """

    def test_lockfile_requires_dist_has_upper_bound(self):
        """Covers T006. Scenario S6 (contract / static).

        Parses uv.lock's [package.metadata] requires-dist entry for `mcp`
        under the mcp-bzm-apitest package and asserts it carries an
        explicit `<2` (or `<2.0.0`) upper bound, mirroring pyproject.toml.
        Today uv.lock records "mcp[cli]>=1.19.0" (no upper bound), so this
        test is expected to FAIL until the lockfile is regenerated (or
        hand-aligned) after T004 lands.
        """
        lockfile_path = REPO_ROOT / "uv.lock"
        lockfile_text = lockfile_path.read_text()

        # Isolate the mcp-bzm-apitest [[package]] block by its boundaries
        # (start of its `name = ...` line through the next `[[package]]`
        # marker or EOF) rather than a single regex -- requires-dist entries
        # contain their own nested `[...]` (e.g. extras = ["cli"]), which
        # breaks a naive non-greedy bracket-matching regex.
        name_marker = 'name = "mcp-bzm-apitest"'
        pkg_start = lockfile_text.find(name_marker)
        assert pkg_start != -1, "Could not find mcp-bzm-apitest package block in uv.lock"
        next_pkg = lockfile_text.find("\n[[package]]", pkg_start)
        package_block = lockfile_text[pkg_start : next_pkg if next_pkg != -1 else len(lockfile_text)]

        requires_dist_start = package_block.find("requires-dist = [")
        assert (
            requires_dist_start != -1
        ), "Could not find requires-dist block under mcp-bzm-apitest in uv.lock"
        requires_dist_block = package_block[requires_dist_start:]

        # Each requires-dist entry is a single-line `{ ... },` -- match the
        # mcp entry's own line, which ends at `},` rather than the first
        # bare `}` (avoids stopping inside a nested `extras = [...]`).
        mcp_entry_pattern = re.compile(r'\{\s*name = "mcp".*?\},')
        mcp_entry_match = mcp_entry_pattern.search(requires_dist_block)
        assert mcp_entry_match, (
            "Could not find an 'mcp' requires-dist entry under " "mcp-bzm-apitest in uv.lock"
        )
        mcp_entry = mcp_entry_match.group(0)

        upper_bound_pattern = re.compile(r"<\s*2(\.0(\.0)?)?(?!\d)")
        assert upper_bound_pattern.search(mcp_entry), (
            f"uv.lock requires-dist entry for mcp has no upper bound: "
            f"'{mcp_entry}'. FR-006: the lockfile must remain consistent "
            f"with the pyproject.toml mcp[cli]>=1.19.0,<2 cap. Regenerate "
            f"uv.lock (uv lock) after the pyproject.toml fix lands, or "
            f"hand-align the specifier."
        )
