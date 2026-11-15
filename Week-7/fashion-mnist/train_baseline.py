"""Baseline: the PyTorch Quickstart tutorial on Fashion-MNIST.

ToTensor, batch size 64, SGD lr=1e-3, CrossEntropyLoss, 5 epochs.
Saves models/baseline.pth and metrics/baseline.json, and exports the model
into cog-baseline/.

Usage: python train_baseline.py
"""

import time

import torch
from torch import nn
from torch.utils.data import DataLoader

from common import (METRICS_DIR, MODELS_DIR, SEED, count_parameters, export_to_cog,
                    get_device, load_datasets, save_json, test, train)
from model import NeuralNetwork

BATCH_SIZE = 64
LEARNING_RATE = 1e-3
EPOCHS = 5


def main():
    torch.manual_seed(SEED)
    device = get_device()
    print(f"Using {device} device")

    training_data, test_data = load_datasets()
    train_dataloader = DataLoader(training_data, batch_size=BATCH_SIZE)
    test_dataloader = DataLoader(test_data, batch_size=BATCH_SIZE)

    model = NeuralNetwork().to(device)
    print(model)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=LEARNING_RATE)

    history = []
    start = time.perf_counter()
    for t in range(EPOCHS):
        print(f"Epoch {t + 1}\n-------------------------------")
        train_loss = train(train_dataloader, model, loss_fn, optimizer, device, log_every=100)
        accuracy, test_loss = test(test_dataloader, model, loss_fn, device)
        print(f"Test Error: \n Accuracy: {100 * accuracy:>0.1f}%, Avg loss: {test_loss:>8f} \n")
        history.append({"epoch": t + 1, "train_loss": round(train_loss, 4),
                        "test_accuracy": round(accuracy, 4), "test_loss": round(test_loss, 4)})
    train_time = time.perf_counter() - start
    print("Done!")

    MODELS_DIR.mkdir(exist_ok=True)
    weights_path = MODELS_DIR / "baseline.pth"
    torch.save(model.state_dict(), weights_path)
    print(f"Saved PyTorch Model State to {weights_path}")

    metrics = {
        "model_name": "fashion-baseline",
        "dataset": "Fashion-MNIST",
        "test_accuracy": round(accuracy, 4),
        "test_loss": round(test_loss, 4),
        "epochs": EPOCHS,
        "train_time_sec": round(train_time, 1),
        "num_parameters": count_parameters(model),
        "device": str(device),
        "hyperparameters": {"optimizer": "SGD", "lr": LEARNING_RATE, "momentum": 0.0,
                            "batch_size": BATCH_SIZE, "hidden_size": 512, "dropout": 0.0,
                            "weight_decay": 0.0, "transform": "ToTensor"},
        "history": history,
    }
    save_json(METRICS_DIR / "baseline.json", metrics)
    export_to_cog("cog-baseline", weights_path, {
        "model_name": "fashion-baseline", "architecture": "NeuralNetwork",
        "kwargs": {}, "test_accuracy": metrics["test_accuracy"]})
    print(f"Test accuracy {accuracy:.4f}, training time {train_time:.1f}s")


if __name__ == "__main__":
    main()
