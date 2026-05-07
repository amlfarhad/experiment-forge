import json
import subprocess
import sys


def test_platform_demo_cli_builds_full_artifact_set(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "forge.py",
            "demo",
            "--workspace",
            str(tmp_path),
            "--users",
            "700",
            "--seed",
            "42",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "generated demo data" in result.stdout.lower()
    assert "built warehouse" in result.stdout.lower()
    assert "quality audit" in result.stdout.lower()
    assert "experiment analysis" in result.stdout.lower()
    assert "wrote reports" in result.stdout.lower()

    assert (tmp_path / "data" / "warehouse" / "experiment_forge.duckdb").exists()
    assert (tmp_path / "reports" / "sample_quality_audit.md").exists()
    assert (tmp_path / "reports" / "sample_experiment_readout.md").exists()
    assert (tmp_path / "reports" / "dashboard.html").exists()

    analysis_payload = json.loads((tmp_path / "reports" / "analysis.json").read_text())
    assert analysis_payload["experiment_name"] == "checkout_progress_indicator"
