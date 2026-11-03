"""Write a Cog prediction payload for a photo.

Usage:
    python make_payload.py test_images/siamese.jpg [payload.json]

The output looks like {"input": {"image": "data:image/jpeg;base64,..."}}
and can be sent with:
    curl -X POST http://localhost:5002/predictions \
         -H "Content-Type: application/json" -d @payload.json
"""

import base64
import json
import mimetypes
import sys
from pathlib import Path


def make_payload(image_path):
    """Return the prediction payload dict for one image file."""
    path = Path(image_path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"input": {"image": f"data:{mime};base64,{encoded}"}}


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("Usage: python make_payload.py <image> [output.json]")
    image_path = sys.argv[1]
    output_path = Path(sys.argv[2] if len(sys.argv) == 3 else "payload.json")
    if not Path(image_path).is_file():
        sys.exit(f"File not found: {image_path}")

    output_path.write_text(json.dumps(make_payload(image_path)), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size:,} bytes) for {image_path}")


if __name__ == "__main__":
    main()
