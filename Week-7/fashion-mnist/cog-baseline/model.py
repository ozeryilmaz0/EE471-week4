"""Fashion-MNIST model from the PyTorch Quickstart tutorial.

The defaults (hidden_size=512, dropout=0.0) build exactly the tutorial network:
Flatten -> Linear(784, 512) -> ReLU -> Linear(512, 512) -> ReLU -> Linear(512, 10).
"""

from torch import nn

CLASSES = [
    "T-shirt/top", "Trouser", "Pullover", "Dress", "Coat",
    "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot",
]


class NeuralNetwork(nn.Module):
    def __init__(self, hidden_size=512, dropout=0.0):
        super().__init__()
        self.flatten = nn.Flatten()
        layers = [nn.Linear(28 * 28, hidden_size), nn.ReLU()]
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        layers += [nn.Linear(hidden_size, hidden_size), nn.ReLU()]
        if dropout > 0:
            layers.append(nn.Dropout(dropout))
        layers.append(nn.Linear(hidden_size, len(CLASSES)))
        self.linear_relu_stack = nn.Sequential(*layers)

    def forward(self, x):
        x = self.flatten(x)
        logits = self.linear_relu_stack(x)
        return logits


def build_model(architecture="NeuralNetwork", **kwargs):
    """Create a model by name (used by the Cog runner and the training scripts)."""
    if architecture != "NeuralNetwork":
        raise ValueError(f"Unknown architecture: {architecture}")
    return NeuralNetwork(**kwargs)
