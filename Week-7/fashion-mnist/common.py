"""Helpers shared by train_baseline.py, hpo.py and train_optimized.py."""

import json
import shutil
from pathlib import Path

import torch
from torch.utils.data import random_split
from torchvision import datasets
from torchvision.transforms import ToTensor

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
METRICS_DIR = ROOT / "metrics"
SEED = 42
VAL_FRACTION = 0.1


def get_device():
    """Use the NVIDIA GPU when there is one, otherwise the CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_datasets():
    """Return the Fashion-MNIST train and test sets (downloaded into data/)."""
    train = datasets.FashionMNIST(root=DATA_DIR, train=True, download=True, transform=ToTensor())
    test = datasets.FashionMNIST(root=DATA_DIR, train=False, download=True, transform=ToTensor())
    return train, test


def split_train_val(train_data):
    """Split the train set into 90% train / 10% validation with a fixed seed."""
    n_val = int(len(train_data) * VAL_FRACTION)
    generator = torch.Generator().manual_seed(SEED)
    return random_split(train_data, [len(train_data) - n_val, n_val], generator=generator)


def train(dataloader, model, loss_fn, optimizer, device, log_every=0):
    """One epoch of training (the Quickstart train loop). Returns the mean batch loss."""
    model.train()
    size = len(dataloader.dataset)
    total_loss = 0.0
    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device)

        # Compute prediction error
        pred = model(X)
        loss = loss_fn(pred, y)

        # Backpropagation
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        total_loss += loss.item()
        if log_every and batch % log_every == 0:
            current = (batch + 1) * len(X)
            print(f"loss: {loss.item():>7f}  [{current:>5d}/{size:>5d}]")
    return total_loss / len(dataloader)


def test(dataloader, model, loss_fn, device):
    """Evaluate the model (the Quickstart test loop). Returns (accuracy, mean loss)."""
    model.eval()
    num_batches = len(dataloader)
    size = len(dataloader.dataset)
    test_loss, correct = 0.0, 0
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            pred = model(X)
            test_loss += loss_fn(pred, y).item()
            correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    return correct / size, test_loss / num_batches


def make_optimizer(name, params, lr, weight_decay=0.0):
    """Create one of the optimizers searched by the HPO."""
    if name == "SGD":
        return torch.optim.SGD(params, lr=lr, momentum=0.9, weight_decay=weight_decay)
    if name == "Adam":
        return torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
    if name == "AdamW":
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    raise ValueError(f"Unknown optimizer: {name}")


def count_parameters(model):
    return sum(p.numel() for p in model.parameters())


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def export_to_cog(cog_dir, weights_path, info):
    """Copy model.py and the weights into a Cog folder and write model_info.json."""
    cog_dir = ROOT / cog_dir
    shutil.copy(ROOT / "model.py", cog_dir / "model.py")
    shutil.copy(weights_path, cog_dir / weights_path.name)
    save_json(cog_dir / "model_info.json", {**info, "weights": weights_path.name})
