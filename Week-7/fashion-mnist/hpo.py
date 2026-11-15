"""Hyperparameter optimization for the Fashion-MNIST network with Optuna.

TPE sampler (seed 42), MedianPruner, 20 trials x 3 epochs. Each trial trains on
90% of the train set and is scored on the other 10% (validation). The test set
is never used here.

Outputs in metrics/: hpo_trials.csv, best_params.json, param_importances.json,
optimization_history.png, param_importances.png.

Usage: python hpo.py [--trials 20] [--epochs 3]
"""

import argparse
import json
import time

import matplotlib
import optuna
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader

from common import (METRICS_DIR, SEED, get_device, load_datasets, make_optimizer, save_json,
                    split_train_val, test, train)
from model import NeuralNetwork

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

SERIES, BEST, MUTED, INK, INK2 = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#52514e"


def suggest_params(trial):
    """The search space."""
    return {
        "optimizer": trial.suggest_categorical("optimizer", ["SGD", "Adam", "AdamW"]),
        "lr": trial.suggest_float("lr", 1e-4, 1e-1, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [32, 64, 128, 256]),
        "hidden_size": trial.suggest_categorical("hidden_size", [128, 256, 512, 1024]),
        "dropout": trial.suggest_float("dropout", 0.0, 0.5),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }


def make_objective(train_set, val_set, device, epochs):
    def objective(trial):
        params = suggest_params(trial)
        torch.manual_seed(SEED)
        train_loader = DataLoader(train_set, batch_size=params["batch_size"], shuffle=True)
        val_loader = DataLoader(val_set, batch_size=512)

        model = NeuralNetwork(params["hidden_size"], params["dropout"]).to(device)
        loss_fn = nn.CrossEntropyLoss()
        optimizer = make_optimizer(params["optimizer"], model.parameters(),
                                   params["lr"], params["weight_decay"])

        val_accuracy = 0.0
        for epoch in range(epochs):
            train(train_loader, model, loss_fn, optimizer, device)
            val_accuracy, val_loss = test(val_loader, model, loss_fn, device)
            trial.report(val_accuracy, epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return val_accuracy
    return objective


def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d6d5cf")
    ax.grid(axis="y", color="#ecebe6", linewidth=0.8)
    ax.set_axisbelow(True)


def plot_history(trials, path, title):
    """Validation accuracy of every trial (from the trials table), plus the best-so-far line."""
    complete = trials[trials["state"] == "COMPLETE"]
    pruned = trials[trials["state"] == "PRUNED"]  # value = last reported validation accuracy
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    ax.scatter(complete["number"], complete["value"], s=28, color=SERIES,
               edgecolor="white", linewidth=1, zorder=3, label="Complete trial")
    if len(pruned):
        ax.scatter(pruned["number"], pruned["value"], s=28, color=MUTED, marker="x",
                   zorder=3, label="Pruned trial (last value)")
    ax.step(complete["number"], complete["value"].cummax(), where="post", color=BEST,
            linewidth=2, label="Best so far")
    style_axes(ax, title, "Trial", "Validation accuracy")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    values = trials["value"].dropna()
    ax.set_ylim(max(0.0, values.min() - 0.03), min(1.0, values.max() + 0.02))
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, ncol=3,
              loc="upper center", bbox_to_anchor=(0.5, -0.2))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def plot_importances(importances, path, title):
    names = list(importances)[::-1]
    values = [importances[n] for n in names]
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=150)
    ax.barh(names, values, color=SERIES, height=0.6)
    for y, v in enumerate(values):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=8, color=INK2)
    style_axes(ax, title, "Importance (fANOVA)", "")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#ecebe6", linewidth=0.8)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_results(study, out_dir, epochs, hpo_time, device):
    """Write the trial table, best parameters, importances and the two plots."""
    out_dir.mkdir(exist_ok=True)
    trials = study.trials_dataframe()
    trials.to_csv(out_dir / "hpo_trials.csv", index=False)
    importances = {k: round(float(v), 4) for k, v in optuna.importance.get_param_importances(
        study, evaluator=optuna.importance.FanovaImportanceEvaluator(seed=SEED)).items()}
    states = [t.state.name for t in study.trials]
    save_json(out_dir / "best_params.json", {
        "best_trial": study.best_trial.number,
        "best_val_accuracy": round(study.best_value, 4),
        "params": study.best_params,
        "n_trials": len(study.trials),
        "n_complete": states.count("COMPLETE"),
        "n_pruned": states.count("PRUNED"),
        "epochs_per_trial": epochs,
        "hpo_time_sec": round(hpo_time, 1),
        "device": str(device),
    })
    save_json(out_dir / "param_importances.json", importances)
    plot_history(trials, out_dir / "optimization_history.png",
                 "Fashion-MNIST: Optuna optimization history")
    plot_importances(importances, out_dir / "param_importances.png",
                     "Fashion-MNIST: hyperparameter importance")

    print(f"Best trial {study.best_trial.number}: val accuracy {study.best_value:.4f}")
    print(f"Best params: {study.best_params}")
    print(f"Importances: {importances}")
    print(f"HPO time {hpo_time:.1f}s")


def replot(out_dir):
    """Redraw both plots from the saved trial table and importances."""
    trials = pd.read_csv(out_dir / "hpo_trials.csv")
    importances = json.loads((out_dir / "param_importances.json").read_text())
    plot_history(trials, out_dir / "optimization_history.png",
                 "Fashion-MNIST: Optuna optimization history")
    plot_importances(importances, out_dir / "param_importances.png",
                     "Fashion-MNIST: hyperparameter importance")
    print("Plots redrawn in", out_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--replot", action="store_true",
                        help="only redraw the plots from metrics/hpo_trials.csv")
    args = parser.parse_args()
    if args.replot:
        replot(METRICS_DIR)
        return

    device = get_device()
    print(f"Using {device} device")
    train_data, _ = load_datasets()  # the test set is not used for HPO
    train_set, val_set = split_train_val(train_data)
    print(f"Train {len(train_set)}, validation {len(val_set)}")

    optuna.logging.set_verbosity(optuna.logging.INFO)
    study = optuna.create_study(
        study_name="fashion-mnist", direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=SEED),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1))
    start = time.perf_counter()
    study.optimize(make_objective(train_set, val_set, device, args.epochs), n_trials=args.trials)
    hpo_time = time.perf_counter() - start

    save_results(study, METRICS_DIR, args.epochs, hpo_time, device)


if __name__ == "__main__":
    main()
