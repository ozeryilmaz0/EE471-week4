"""Train the CIFAR-10 CNN with the best HPO parameters.

Reads metrics/best_params.json, trains for up to 20 epochs on the 90% train
split with early stopping on validation accuracy (patience 5), keeps the best
epoch, then measures the test set once. Saves models/optimized.pth and
metrics/optimized.json, and exports the model into cog-optimized/.

Usage: python train_optimized.py [--epochs 20] [--patience 5]
"""

import argparse
import copy
import json
import time

import torch
from torch import nn

from common import (METRICS_DIR, MODELS_DIR, SEED, cifar, count_parameters, export_to_cog,
                    get_device, loader, make_optimizer, save_json, test, train, train_val_sets)
from model import CifarCNN


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=5)
    args = parser.parse_args()

    params = json.loads((METRICS_DIR / "best_params.json").read_text())["params"]
    print(f"Best params: {params}")
    torch.manual_seed(SEED)
    device = get_device()
    print(f"Using {device} device")

    train_set, val_set = train_val_sets(params["augment"])
    train_loader = loader(train_set, params["batch_size"], shuffle=True)
    val_loader = loader(val_set, 512, shuffle=False)
    test_loader = loader(cifar(False), 512, shuffle=False)

    model_kwargs = {"width": params["width"], "dropout": params["dropout"],
                    "batchnorm": params["batchnorm"]}
    model = CifarCNN(**model_kwargs).to(device)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = make_optimizer(params["optimizer"], model.parameters(),
                               params["lr"], params["weight_decay"])

    history, best_acc, best_epoch, best_state = [], -1.0, 0, None
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        train_loss = train(train_loader, model, loss_fn, optimizer, device)
        val_acc, val_loss = test(val_loader, model, loss_fn, device)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 4),
                        "val_accuracy": round(val_acc, 4), "val_loss": round(val_loss, 4)})
        print(f"Epoch {epoch:2d}: train loss {train_loss:.4f}, "
              f"val accuracy {100 * val_acc:.2f}%, val loss {val_loss:.4f}", flush=True)
        if val_acc > best_acc:
            best_acc, best_epoch = val_acc, epoch
            best_state = copy.deepcopy(model.state_dict())
        elif epoch - best_epoch >= args.patience:
            print(f"Early stopping: no improvement for {args.patience} epochs")
            break
    train_time = time.perf_counter() - start

    model.load_state_dict(best_state)
    test_acc, test_loss = test(test_loader, model, loss_fn, device)
    print(f"Best epoch {best_epoch} (val {100 * best_acc:.2f}%) -> "
          f"test accuracy {100 * test_acc:.2f}%, test loss {test_loss:.4f}")

    MODELS_DIR.mkdir(exist_ok=True)
    weights_path = MODELS_DIR / "optimized.pth"
    torch.save(model.state_dict(), weights_path)

    save_json(METRICS_DIR / "optimized.json", {
        "model_name": "cifar-optimized",
        "dataset": "CIFAR-10",
        "test_accuracy": round(test_acc, 4),
        "test_loss": round(test_loss, 4),
        "epochs": len(history),
        "max_epochs": args.epochs,
        "best_epoch": best_epoch,
        "best_val_accuracy": round(best_acc, 4),
        "train_time_sec": round(train_time, 1),
        "num_parameters": count_parameters(model),
        "device": str(device),
        "hyperparameters": params,
        "history": history,
    })
    export_to_cog("cog-optimized", weights_path, {
        "model_name": "cifar-optimized", "architecture": "CifarCNN",
        "kwargs": model_kwargs, "test_accuracy": round(test_acc, 4)})


if __name__ == "__main__":
    main()
