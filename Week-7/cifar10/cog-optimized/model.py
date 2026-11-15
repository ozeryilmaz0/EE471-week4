"""CIFAR-10 models.

Net: the network from the PyTorch "Training a Classifier" tutorial
     (conv 6 -> conv 16 -> fc 120 -> fc 84 -> fc 10).
CifarCNN: a configurable VGG-style CNN whose width, dropout and batch norm are
          chosen by the hyperparameter search.
"""

import torch
import torch.nn.functional as F
from torch import nn

CLASSES = ("plane", "car", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck")


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1)  # flatten all dimensions except batch
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def conv_block(in_ch, out_ch, batchnorm):
    """Two 3x3 convolutions (+ optional batch norm) followed by 2x2 max pooling."""
    layers = []
    for c_in in (in_ch, out_ch):
        layers.append(nn.Conv2d(c_in, out_ch, 3, padding=1, bias=not batchnorm))
        if batchnorm:
            layers.append(nn.BatchNorm2d(out_ch))
        layers.append(nn.ReLU(inplace=True))
    layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)


class CifarCNN(nn.Module):
    """3 conv blocks with width, 2*width and 4*width channels: 32x32 -> 4x4."""

    def __init__(self, width=32, dropout=0.3, batchnorm=True):
        super().__init__()
        self.features = nn.Sequential(
            conv_block(3, width, batchnorm),
            conv_block(width, 2 * width, batchnorm),
            conv_block(2 * width, 4 * width, batchnorm),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(4 * width * 4 * 4, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, len(CLASSES)),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


def build_model(architecture, **kwargs):
    """Create a model by name (used by the Cog runner and the training scripts)."""
    models = {"Net": Net, "CifarCNN": CifarCNN}
    if architecture not in models:
        raise ValueError(f"Unknown architecture: {architecture}")
    return models[architecture](**kwargs)
