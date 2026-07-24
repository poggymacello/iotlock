"""Command-line entry point: ``python -m iotlock train|eval``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from iotlock import evaluate as eval_mod
from iotlock.animate import animate_cascade
from iotlock.artifact import artifact_path_for_version, build_artifact, save_artifact
from iotlock.botnet_data import DEVICES, device_holdout_split, load_all_devices
from iotlock.detection import run_detection_pipeline
from iotlock.mitigation_real_pipeline import (
    run_centrality_impact_across_topologies,
    run_mitigation_across_topologies,
)
from iotlock.simulation import STRATEGIES, simulate_cascade
from iotlock.topology import build_topology, compute_centrality
from iotlock.topology_real import load_topologies


def _run_pipeline(n_nodes: int, m: int, n_trials: int, max_timesteps: int, seed: int) -> dict:
    graph = build_topology(n_nodes=n_nodes, m=m, seed=seed)
    centrality = compute_centrality(graph)

    curves = {
        strategy: eval_mod.survival_curve(
            graph, strategy, n_trials=n_trials, max_timesteps=max_timesteps, seed=seed
        )
        for strategy in STRATEGIES
    }

    # a shorter horizon than the main survival curves: at the full horizon
    # the "none" cascade tends to consume nearly the whole network
    # regardless of which node started it (a ceiling effect), which washes
    # out the centrality signal entirely
    centrality_values, impacts, correlation = eval_mod.centrality_vs_impact(
        graph, centrality, n_trials=max(3, n_trials // 5), max_timesteps=10, seed=seed
    )

    baseline_history = simulate_cascade(
        graph, strategy="none", max_timesteps=max_timesteps, seed=seed
    )

    return {
        "graph": graph,
        "curves": curves,
        "centrality_values": centrality_values,
        "impacts": impacts,
        "correlation": correlation,
        "baseline_history": baseline_history,
    }


def cmd_train(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = _run_pipeline(args.n_nodes, args.m, args.n_trials, args.max_timesteps, args.seed)

    metrics = {
        strategy: {
            "final_survival_pct": round(float(curve[-1] * 100), 2),
            "time_to_50pct_saturation": eval_mod.time_to_saturation(curve, threshold=0.5),
        }
        for strategy, curve in result["curves"].items()
    }
    metrics["centrality_impact_correlation"] = round(result["correlation"], 4)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    eval_mod.plot_survival_curves(result["curves"], out_dir / "survival_curves.png")
    eval_mod.plot_centrality_vs_impact(
        result["centrality_values"],
        result["impacts"],
        result["correlation"],
        out_dir / "centrality_vs_impact.png",
    )

    anim = animate_cascade(result["graph"], result["baseline_history"])
    anim.save(out_dir / "simulasi_ddos.gif", writer="pillow")

    print(json.dumps(metrics, indent=2))
    print(f"\nartifacts written to {out_dir}/")


def cmd_eval(args: argparse.Namespace) -> None:
    result = _run_pipeline(args.n_nodes, args.m, args.n_trials, args.max_timesteps, args.seed)
    for strategy, curve in result["curves"].items():
        print(
            f"{strategy}: final survival {curve[-1] * 100:.1f}%, "
            f"time-to-50%-saturation {eval_mod.time_to_saturation(curve)}"
        )
    print(f"centrality-impact correlation: {result['correlation']:.4f}")


def cmd_real_train(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("loading real Internet Topology Zoo networks...")
    topologies = load_topologies()
    print(f"{len(topologies)} connected topologies in range")

    print("running Monte Carlo mitigation across all real topologies...")
    mitigation = run_mitigation_across_topologies(
        topologies, n_trials=args.n_trials, seed=args.seed
    )

    print("revalidating centrality-impact correlation across all real topologies...")
    centrality = run_centrality_impact_across_topologies(topologies, seed=args.seed)

    print("running the N-BaIoT botnet detector (device-holdout split)...")
    detection = run_detection_pipeline(seed=args.seed, test_device=args.test_device)

    report = {
        "n_topologies": mitigation["n_topologies"],
        "survival_distribution_pct": mitigation["survival_distribution_pct"],
        "centrality_impact_correlation_distribution": centrality["correlation_distribution"],
        "n_topologies_with_valid_correlation": centrality["n_topologies_with_valid_correlation"],
        "detection_metrics": detection["metrics"],
        "detection_polarity_flag": detection["polarity_flag"],
        "detection_base_rates": detection["base_rates"],
        "detection_n_suspicious_features": detection["n_suspicious_features"],
    }
    (out_dir / "metrics_real.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    eval_mod.plot_correlation_distribution(
        list(centrality["per_topology_correlation"].values()),
        out_dir / "centrality_vs_impact_real.png",
    )

    # a representative real topology for the animation: the largest one
    # in the filtered set, so the cascade's structure is visually legible
    demo_name, demo_graph = max(topologies, key=lambda t: t[1].number_of_nodes())
    baseline_history = simulate_cascade(
        demo_graph, strategy="none", max_timesteps=20, seed=args.seed
    )
    anim = animate_cascade(demo_graph, baseline_history)
    anim.save(out_dir / "simulasi_ddos_real.gif", writer="pillow")
    print(f"animation topology: {demo_name} ({demo_graph.number_of_nodes()} nodes)")

    print("\ntraining and saving the deployed botnet-detection artifact...")
    full_dataset = load_all_devices(devices=DEVICES, seed=args.seed)
    train, _test = device_holdout_split(full_dataset, test_device=args.test_device)
    artifact = build_artifact(train.X, train.y, test_device=args.test_device, seed=args.seed)
    path = artifact_path_for_version(Path(args.models_dir))
    save_artifact(artifact, path)
    print(f"model artifact written to {path}")

    print(f"\nartifacts written to {out_dir}/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="iotlock")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--n-nodes", type=int, default=40)
    common.add_argument("--m", type=int, default=2)
    common.add_argument("--n-trials", type=int, default=30)
    common.add_argument("--max-timesteps", type=int, default=20)
    common.add_argument("--seed", type=int, default=42)

    train_p = sub.add_parser("train", parents=[common], help="run + evaluate + save artifacts")
    train_p.add_argument("--output-dir", default="assets")
    train_p.set_defaults(func=cmd_train)

    eval_p = sub.add_parser(
        "eval", parents=[common], help="re-run the deterministic pipeline and print metrics"
    )
    eval_p.set_defaults(func=cmd_eval)

    real_train_p = sub.add_parser(
        "real-train",
        help="run the mitigation + centrality + detection pipelines on real data",
    )
    real_train_p.add_argument("--seed", type=int, default=42)
    real_train_p.add_argument("--n-trials", type=int, default=20)
    real_train_p.add_argument(
        "--test-device", default="SimpleHome_XCS7_1003_WHT_Security_Camera"
    )
    real_train_p.add_argument("--output-dir", default="assets")
    real_train_p.add_argument("--models-dir", default="models")
    real_train_p.set_defaults(func=cmd_real_train)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
