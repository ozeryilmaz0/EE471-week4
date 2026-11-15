"""Baseline: the PyTorch "Training a Classifier" tutorial on CIFAR-10.

Normalize(0.5), batch size 4, SGD lr=0.001 momentum=0.9, CrossEntropyLoss, 2 epochs.
Saves models/baseline.pth and metrics/baseline.json, and exports the model
into cog-baseline/.

Usage: python train_baseline.py
"""

import time

import torch
import torch.nn as nn
import torch.optim as optim

from common import (METRICS_DIR, MODELS_DIR, SEED, count_parameters, cifar, export_to_cog,
                    get_device, loader, save_json, test, train)
from model import Net

BATCH_SIZE = 4
LEARNING_RATE = 0.001
MOMENTUM = 0.9
EPOCHS = 2


def main():
    torch.manual_seed(SEED)
    device = get_device()
    print(f"Using {device} device")

    trainloader = loader(cifar(True), BATCH_SIZE, shuffle=True)
    testloader = loader(cifar(False), BATCH_SIZE, shuffle=False)

    net = Net().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=LEARNING_RATE, momentum=MOMENTUM)

    history = []
    start = time.perf_counter()
    for epoch in range(EPOCHS):  # loop over the dataset multiple times
        print(f"Epoch {epoch + 1}")
        train_loss = train(trainloader, net, criterion, optimizer, device, log_every=2000)
        accuracy, test_loss = test(testloader, net, criterion, device)
        print(f"Accuracy of the network on the 10000 test images: {100 * accuracy:.1f} %")
        history.append({"epoch": epoch + 1, "train_loss": round(train_loss, 4),
                        "test_accuracy": round(accuracy, 4), "test_loss": round(test_loss, 4)})
    train_time = time.perf_counter() - start
    print("Finished Training")

    MODELS_DIR.mkdir(exist_ok=True)
    weights_path = MODELS_DIR / "baseline.pth"
    torch.save(net.state_dict(), weights_path)

    metrics = {
        "model_name": "cifar-baseline",
        "dataset": "CIFAR-10",
        "test_accuracy": round(accuracy, 4),
        "test_loss": round(test_loss, 4),
        "epochs": EPOCHS,
        "train_time_sec": round(train_time, 1),
        "num_parameters": count_parameters(net),
        "device": str(device),
        "hyperparameters": {"optimizer": "SGD", "lr": LEARNING_RATE, "momentum": MOMENTUM,
                            "batch_size": BATCH_SIZE, "weight_decay": 0.0,
                            "transform": "ToTensor + Normalize(0.5)", "augment": False},
        "history": history,
    }
    save_json(METRICS_DIR / "baseline.json", metrics)
    export_to_cog("cog-baseline", weights_path, {
        "model_name": "cifar-baseline", "architecture": "Net",
        "kwargs": {}, "test_accuracy": metrics["test_accuracy"]})
    print(f"Test accuracy {accuracy:.4f}, training time {train_time:.1f}s")


if __name__ == "__main__":
    main()
