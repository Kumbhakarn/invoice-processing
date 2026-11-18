"""Write an inventory of licenses for every registry package in uv.lock."""

from __future__ import annotations

import concurrent.futures
import json
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = BACKEND_ROOT / "uv.lock"
OUTPUT_PATH = BACKEND_ROOT.parent / "docs" / "dependency-licenses.md"
UPSTREAM_LICENSE_OVERRIDES = {
    "mypy-extensions": "MIT (upstream LICENSE; PyPI metadata omits license)"
}


def _license(package: dict[str, Any]) -> tuple[str, str, str]:
    name = str(package["name"])
    version = str(package["version"])
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    request = urllib.request.Request(url, headers={"User-Agent": "DocExtract-license-inventory"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            metadata = json.load(response)["info"]
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as error:
        return name, version, f"METADATA UNAVAILABLE ({type(error).__name__})"

    expression = metadata.get("license_expression")
    raw_license = metadata.get("license")
    classifiers = metadata.get("classifiers", [])
    osi = [
        item.removeprefix("License :: OSI Approved :: ")
        for item in classifiers
        if item.startswith("License :: OSI Approved :: ")
    ]
    if expression:
        license_name = str(expression)
    elif osi:
        license_name = "; ".join(sorted(set(osi)))
    elif raw_license and len(str(raw_license)) < 100:
        license_name = " ".join(str(raw_license).split())
    else:
        license_name = "UNSPECIFIED by PyPI release metadata"
    if license_name == "UNSPECIFIED by PyPI release metadata":
        license_name = UPSTREAM_LICENSE_OVERRIDES.get(name, license_name)
    return name, version, license_name


def main() -> None:
    lock = tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))
    packages = [
        package
        for package in lock["package"]
        if package.get("source", {}).get("registry", "").startswith("https://pypi.org/")
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        licenses = sorted(executor.map(_license, packages), key=lambda item: item[0].casefold())

    rows = [
        "# Locked dependency license inventory",
        "",
        (
            f"Generated from `backend/uv.lock`: {len(licenses)} registry packages "
            "(including transitive and optional dependencies)."
        ),
        (
            "License labels are read from the exact release's PyPI metadata; release pages "
            "are linked for review. `UNSPECIFIED` means release metadata did not declare "
            "a license and needs maintainer review."
        ),
        "",
        "| Package | Locked version | Declared license |",
        "| --- | ---: | --- |",
    ]
    rows.extend(
        f"| [{name}](https://pypi.org/project/{name}/{version}/) | `{version}` | {license_name} |"
        for name, version, license_name in licenses
    )
    OUTPUT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")
    unspecified = [
        item
        for item in licenses
        if "UNSPECIFIED" in item[2] or "UNAVAILABLE" in item[2]
    ]
    print(f"Wrote {len(licenses)} package entries to {OUTPUT_PATH}")
    if unspecified:
        print(f"Entries needing metadata review: {len(unspecified)}")
        for name, version, label in unspecified:
            print(f"{name}=={version}: {label}")


if __name__ == "__main__":
    main()
