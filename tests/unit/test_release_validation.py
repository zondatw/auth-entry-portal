from __future__ import annotations

from copy import deepcopy
import subprocess
import sys

import pytest

from scripts.release.package_metadata import load_pyproject
from scripts.release.validate_release import ReleaseContext, release_target, validate_release


def valid_context(**changes) -> ReleaseContext:
    values = {
        "action": "published",
        "tag": "v0.4.0",
        "prerelease": False,
        "target_commitish": "beta",
        "target_index": "testpypi",
        "clean": True,
    }
    values.update(changes)
    return ReleaseContext(**values)


def test_valid_stable_release_passes():
    metadata = validate_release(valid_context(), load_pyproject())
    assert str(metadata.version) == "0.4.0"
    assert metadata.target_index == "testpypi"


def test_release_branch_targets_pypi():
    metadata = validate_release(
        valid_context(target_commitish="release", target_index="pypi"),
        load_pyproject(),
    )
    assert str(metadata.version) == "0.4.0"
    assert metadata.target_branch == "release"
    assert metadata.target_index == "pypi"


def test_branch_target_resolution_is_exact():
    assert release_target("beta") == "testpypi"
    assert release_target("release") == "pypi"
    for branch in ("main", "beta-fix", "release-candidate", "releases", "hotfix"):
        with pytest.raises(ValueError, match="release-target-unsupported"):
            release_target(branch)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"action": "created"}, "release-event-not-published"),
        ({"tag": "0.4.0"}, "release-tag-must-start-with-v"),
        ({"tag": "v0.4.1"}, "tag-version-mismatch"),
        ({"prerelease": True}, "release-type-mismatch"),
        ({"target_commitish": "feature"}, "release-target-unsupported"),
        ({"target_commitish": "release"}, "release-target-not-testpypi"),
        ({"target_index": "pypi"}, "release-target-not-pypi"),
        ({"clean": False}, "release-input-not-clean"),
    ],
)
def test_invalid_release_context_fails_with_safe_reason(changes, reason):
    with pytest.raises(ValueError, match=reason):
        validate_release(valid_context(**changes), load_pyproject())


def test_wrong_package_name_and_missing_metadata_fail():
    document = deepcopy(load_pyproject())
    document["project"]["name"] = "auth-entry-portal"
    with pytest.raises(ValueError, match="unexpected-distribution-name"):
        validate_release(valid_context(), document)


def test_prerelease_requires_matching_prerelease_version():
    document = deepcopy(load_pyproject())
    document["project"]["version"] = "0.4.0rc1"
    context = valid_context(tag="v0.4.0rc1", prerelease=True)
    metadata = validate_release(context, document)
    assert metadata.version.is_prerelease


def test_release_validation_cli_reports_safe_reason_without_traceback():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.release.validate_release",
            "--action",
            "published",
            "--tag",
            "v0.4.0",
            "--prerelease",
            "false",
            "--target-commitish",
            "main",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "release-target-unsupported" in result.stderr
    assert "Traceback" not in result.stderr
