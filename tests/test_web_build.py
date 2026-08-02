import json

from web_artifacts import write_web_artifacts


def test_web_artifacts_write_catalog_and_experiment_payloads(tmp_path):
    output_dir = tmp_path / "web" / "data"

    manifest = write_web_artifacts(output_dir, n_users=900, seed=42)

    catalog = json.loads((output_dir / "catalog.json").read_text())
    assert manifest["schema_version"] == "1.0"
    assert len(catalog["experiments"]) == 2
    assert {item["decision"] for item in catalog["experiments"]} == {"investigate", "launch"}

    flawed_path = output_dir / "experiments" / "checkout_progress_indicator.json"
    clean_path = output_dir / "experiments" / "search_autocomplete_refresh.json"
    assert flawed_path.exists()
    assert clean_path.exists()

    flawed = json.loads(flawed_path.read_text())
    clean = json.loads(clean_path.read_text())
    assert flawed["analysis"]["decision"] == "investigate"
    assert clean["analysis"]["decision"] == "launch"
    assert flawed["quality"]["summary"]["failed"] >= 1
    assert clean["quality"]["summary"]["failed"] == 0
    assert clean["segments"]
    assert clean["daily_trend"]
    assert clean["lineage"]


def test_web_artifacts_are_reproducible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_web_artifacts(first, n_users=700, seed=7)
    write_web_artifacts(second, n_users=700, seed=7)

    assert (first / "catalog.json").read_bytes() == (second / "catalog.json").read_bytes()
    assert (
        first / "experiments" / "checkout_progress_indicator.json"
    ).read_bytes() == (second / "experiments" / "checkout_progress_indicator.json").read_bytes()
