"""Cog runner for the face direction classifier. The logic lives in face_direction.py."""

import logging
import sys

from cog import BaseRunner, Input, Path

import face_direction


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
        """Load the face model once; every prediction reuses it."""
        # Cog already configures the root logger, so attach a handler to our own logger.
        if not face_direction.log.handlers:
            handler = CogLogHandler()
            handler.setFormatter(logging.Formatter("[face_direction] %(message)s"))
            face_direction.log.addHandler(handler)
            face_direction.log.setLevel(logging.INFO)
            face_direction.log.propagate = False
        self.landmarker = face_direction.create_landmarker()

    def run(
        self,
        image: Path = Input(description="Photo of a face"),
        perspective: str = Input(
            description="subject = the person's own left/right; viewer = as seen in the image",
            default="subject",
            choices=["subject", "viewer"],
        ),
    ) -> str:
        """Return "left", "right" or "straight". The yaw angle is written to the log."""
        label, _, _ = face_direction.classify(self.landmarker, image, perspective)
        return label
