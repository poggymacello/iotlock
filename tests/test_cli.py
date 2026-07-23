import json

from iotlock.cli import main


def test_train_command_writes_artifacts(tmp_path):
    out_dir = tmp_path / "assets"
    main(
        [
            "train",
            "--n-nodes",
            "15",
            "--n-trials",
            "5",
            "--max-timesteps",
            "8",
            "--seed",
            "1",
            "--output-dir",
            str(out_dir),
        ]
    )

    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "survival_curves.png").exists()
    assert (out_dir / "centrality_vs_impact.png").exists()
    assert (out_dir / "simulasi_ddos.gif").exists()

    metrics = json.loads((out_dir / "metrics.json").read_text())
    assert "none" in metrics
    assert "rate_limit" in metrics
    assert "isolate_failed" in metrics
    assert "centrality_impact_correlation" in metrics


def test_eval_command_runs_without_error(capsys):
    main(["eval", "--n-nodes", "15", "--n-trials", "5", "--max-timesteps", "8", "--seed", "1"])
    captured = capsys.readouterr()
    assert "centrality-impact correlation" in captured.out
