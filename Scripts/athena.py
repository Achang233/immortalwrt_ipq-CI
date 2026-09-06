#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Achang233 <https://github.com/Achang233>

"""Build the checked-out Athena core and adapt its OpenWrt source archive."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib


def make_value(text, key):
    values = re.findall(rf"^{re.escape(key)}:=(.+)$", text, re.MULTILINE)
    if len(values) != 1:
        raise ValueError(f"Expected one {key} definition, found {len(values)}")
    return values[0].strip()


def replace_value(text, key, value):
    make_value(text, key)
    return re.sub(rf"^{re.escape(key)}:=.+$", lambda _: f"{key}:={value}", text, flags=re.MULTILINE)


def output(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def build(source, wrt, target_dir):
    source, wrt, target_dir = source.resolve(), wrt.resolve(), target_dir.resolve()
    core = source / "athena-led"
    makefile = core / "Makefile"
    recipe = makefile.read_text(encoding="utf-8")
    ui_recipe = (source / "luci-app-athena-led/Makefile").read_text(encoding="utf-8")
    cargo = tomllib.loads((core / "Cargo.toml").read_text(encoding="utf-8"))
    version = cargo["package"]["version"]
    if make_value(recipe, "PKG_VERSION") != version or make_value(ui_recipe, "PKG_VERSION") != version:
        raise ValueError("Athena Cargo, core package and LuCI versions must match")
    lock_hash = hashlib.sha256((core / "Cargo.lock").read_bytes()).hexdigest()
    revision = output("git", "rev-parse", "HEAD", cwd=source)
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full Git commit ID")
    # Check the packaging contract before spending time on Rust compilation.
    for key in ("PKG_SOURCE", "PKG_SOURCE_URL", "PKG_HASH"):
        make_value(recipe, key)
    target = "aarch64-unknown-linux-musl"
    print(f"Building Athena {version} from {revision} for {target}", flush=True)
    subprocess.run(
        ["cargo", "zigbuild", "--locked", "--release", "--target", target],
        cwd=core, env={**os.environ, "CARGO_TARGET_DIR": str(target_dir)}, check=True,
    )
    binary = target_dir / target / "release/athena-led"
    if not binary.is_file() or binary.stat().st_size == 0:
        raise ValueError("Rust build did not produce athena-led")
    # Include the commit so unpublished changes with the same version cannot reuse an old archive.
    filename = f"athena-led-{target}-{revision}.tar.gz"
    dist = wrt / "athena-dist"
    dist.mkdir(exist_ok=True)
    archive = dist / filename
    with tarfile.open(archive, "w:gz") as tar:
        info = tar.gettarinfo(str(binary), arcname="athena-led")
        info.mode, info.uid, info.gid = 0o755, 0, 0
        info.uname = info.gname = "root"
        with binary.open("rb") as stream:
            tar.addfile(info, stream)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    recipe = replace_value(recipe, "PKG_SOURCE", filename)
    recipe = replace_value(recipe, "PKG_SOURCE_URL", "file://$(TOPDIR)/athena-dist")
    recipe = replace_value(recipe, "PKG_HASH", digest)
    makefile.write_text(recipe, encoding="utf-8", newline="\n")
    metadata = {
        "repository": "https://github.com/unraveloop/JDC-AX6600-Athena-LED-Controller",
        "commit": revision, "version": version, "target": target,
        "archive": filename, "sha256": digest, "cargo_lock_sha256": lock_hash,
        "rustc": output("rustc", "--version"), "zigbuild": output("cargo-zigbuild", "--version"),
    }
    (wrt / "athena-build.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("wrt", type=Path)
    parser.add_argument("target_dir", type=Path)
    args = parser.parse_args()
    build(args.source, args.wrt, args.target_dir)
