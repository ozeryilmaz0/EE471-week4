"""Build the two Postman v2.1 collections (Fashion and CIFAR) with an embedded sample image.

Each collection has: baseline health-check, optimized health-check,
baseline predict and optimized predict.

Usage: python postman/make_collections.py
"""

import base64
import json
from pathlib import Path

WEEK7 = Path(__file__).resolve().parent.parent
SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

COLLECTIONS = [
    {"file": "fashion.postman_collection.json", "name": "Week 7 - Fashion-MNIST (Cog)",
     "prefix": "fashion", "baseline_port": 5010, "optimized_port": 5011,
     "sample": WEEK7 / "fashion-mnist" / "sample_images" / "09_ankle_boot_1.png"},
    {"file": "cifar.postman_collection.json", "name": "Week 7 - CIFAR-10 (Cog)",
     "prefix": "cifar", "baseline_port": 5020, "optimized_port": 5021,
     "sample": WEEK7 / "cifar10" / "sample_images" / "01_car_1.png"},
]

HEALTH_TEST = [
    'pm.test("Status code is 200", () => pm.response.to.have.status(200));',
    'pm.test("Model is READY", () => pm.expect(pm.response.json().status).to.eql("READY"));',
]
PREDICT_TEST = [
    'pm.test("Status code is 200", () => pm.response.to.have.status(200));',
    "const body = pm.response.json();",
    'pm.test("Prediction succeeded", () => pm.expect(body.status).to.eql("succeeded"));',
    'pm.test("Has predicted_class and top3", () => {',
    '    pm.expect(body.output).to.have.property("predicted_class");',
    '    pm.expect(Object.keys(body.output.top3)).to.have.lengthOf(3);',
    "});",
]


def url(port, path):
    return {"raw": f"http://localhost:{port}/{path}", "protocol": "http",
            "host": ["localhost"], "port": str(port), "path": [path]}


def test_event(lines):
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]


def health_item(name, port):
    return {"name": name, "event": test_event(HEALTH_TEST),
            "request": {"method": "GET", "header": [], "url": url(port, "health-check")}}


def predict_item(name, port, data_uri, sample_name):
    body = json.dumps({"input": {"image": data_uri}}, indent=2)
    return {"name": name, "event": test_event(PREDICT_TEST),
            "request": {"method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {"mode": "raw", "raw": body, "options": {"raw": {"language": "json"}}},
                        "url": url(port, "predictions"),
                        "description": f"Body contains sample_images/{sample_name} as a base64 data URI."}}


def main():
    for c in COLLECTIONS:
        data_uri = "data:image/png;base64," + base64.b64encode(c["sample"].read_bytes()).decode()
        p = c["prefix"]
        collection = {
            "info": {"name": c["name"], "schema": SCHEMA,
                     "description": f"Start the containers with docker compose -f "
                                    f"docker-compose.{p}.yml up -d, then Send each request."},
            "item": [
                health_item(f"{p}-baseline health-check", c["baseline_port"]),
                health_item(f"{p}-optimized health-check", c["optimized_port"]),
                predict_item(f"{p}-baseline predict", c["baseline_port"], data_uri, c["sample"].name),
                predict_item(f"{p}-optimized predict", c["optimized_port"], data_uri, c["sample"].name),
            ],
        }
        out = Path(__file__).resolve().parent / c["file"]
        out.write_text(json.dumps(collection, indent=2), encoding="utf-8")
        print(f"Wrote {out.name} ({out.stat().st_size // 1024} KB, sample {c['sample'].name})")


if __name__ == "__main__":
    main()
