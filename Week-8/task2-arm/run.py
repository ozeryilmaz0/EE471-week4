"""Cog runner for the arm-up classifier. The logic lives in arm_up.py."""

import logging
import sys

from cog import BaseRunner, Input, Path

import arm_up


class CogLogHandler(logging.Handler):
    """Send log lines to both places where Cog shows output.

    * the real stderr (file descriptor 2): shown by `cog run` and `docker logs`
    * the current sys.stdout: Cog swaps it for each prediction and puts it in the
      "logs" field of the HTTP API response
    """

    def emit(self, record):
        line = self.format(record) + "\n"
        for stream in (sys.__stderr__, sys.stdout):
            stream.write(line)
            stream.flush()


class Runner(BaseRunner):
    def setup(self):
        """Load the pose model once; every prediction reuses it."""
        # Cog already configures the root logger, so attach a handler to our own logger.
        if not arm_up.log.handlers:
            handler = CogLogHandler()
            handler.setFormatter(logging.Formatter("[arm_up] %(message)s"))
            arm_up.log.addHandler(handler)
            arm_up.log.setLevel(logging.INFO)
            arm_up.log.propagate = False
        self.landmarker = arm_up.create_landmarker()

    def run(
        self,
        image: Path = Input(description="Photo of a person"),
        perspective: str = Input(
            description="subject = the person's own left/right; viewer = as seen in the image",
            default="subject",
            choices=["subject", "viewer"],
        ),
    ) -> str:
        """Return "left", "right", "both" or "None"."""
        return arm_up.classify(self.landmarker, image, perspective)
