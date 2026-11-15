"""Helpers shared by train_baseline.py, hpo.py and train_optimized.py."""

import json
import shutil
from pathlib import Path

import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset
from torchvision import datasets

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
METRICS_DIR = ROOT / "metrics"
SEED = 42
VAL_FRACTION = 0.1
NUM_WORKERS = 2

# The tutorial transform (also used by the Cog runner).
BASE_TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
])
AUGMENT_TRANSFORM = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    BASE_TRANSFORM,
])


def get_device():
    """Use the NVIDIA GPU when there is one, otherwise the CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def cifar(train, transform=BASE_TRANSFORM):
    return datasets.CIFAR10(root=DATA_DIR, train=train, download=True, transform=transform)


def train_val_sets(augment):
    """Split the train set 90/10 with a fixed seed.

    The train part gets augmentation (if asked); the validation part never does.
    """
    n = len(cifar(True))
    n_val = int(n * VAL_FRACTION)
    order = torch.randperm(n, generator=torch.Generator().manual_seed(SEED)).tolist()
    train_set = Subset(cifar(True, AUGMENT_TRANSFORM if augment else BASE_TRANSFORM), order[n_val:])
    val_set = Subset(cifar(True), order[:n_val])
    return train_set, val_set


def loader(dataset, batch_size, shuffle):
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle,
                      num_workers=NUM_WORKERS, persistent_workers=True,
                      pin_memory=torch.cuda.is_available())


def train(dataloader, model, loss_fn, optimizer, device, log_every=0):
    """One epoch of training. Returns the mean batch loss."""
    model.train()
    total_loss, running_loss = 0.0, 0.0
    for i, (inputs, labels) in enumerate(dataloader):
        inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        outputs = model(inputs)
        loss = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        running_loss += loss.item()
        if log_every and i % log_every == log_every - 1:
            print(f"[{i + 1:5d}] loss: {running_loss / log_every:.3f}")
            running_loss = 0.0
    return total_loss / len(dataloader)


def test(dataloader, model, loss_fn, device):
    """Evaluate the model. Returns (accuracy, mean batch loss)."""
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            total_loss += loss_fn(outputs, labels).item()
            correct += (outputs.argmax(1) == labels).sum().item()
            total += labels.size(0)
    return correct / total, total_loss / len(dataloader)


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
