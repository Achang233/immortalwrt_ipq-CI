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


DEVICE_NAME = "jdcloud_re-cs-02"
APP_PACKAGE = "luci-app-athena-led"
TRANSLATION_PACKAGE = "luci-i18n-athena-led-zh-cn"
EMBEDDED_TRANSLATION = "athena_led.zh-cn.lmo"


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


def ui_recipe(source):
    return (source.resolve() / "luci-app-athena-led/Makefile").read_text(encoding="utf-8")


def adapt_device_packages(wrt, ui_recipe):
    """Install Athena only for AX6600 and match the LuCI translation layout."""
    image = wrt / "target/linux/qualcommax/image/ipq60xx.mk"
    text = image.read_text(encoding="utf-8")
    pattern = rf"(?ms)^define Device/{re.escape(DEVICE_NAME)}\n.*?^endef$"
    blocks = list(re.finditer(pattern, text))
    if len(blocks) != 1:
        raise ValueError(f"Expected one Device/{DEVICE_NAME} definition, found {len(blocks)}")
    block = blocks[0].group()
    app_count = len(re.findall(rf"(?<!\S){re.escape(APP_PACKAGE)}(?=\s|$)", block))
    if app_count > 1:
        raise ValueError(f"Expected at most one {APP_PACKAGE}, found {app_count}")
    changed = False
    if app_count == 0:
        block = block.removesuffix("endef") + f"  DEVICE_PACKAGES += {APP_PACKAGE}\nendef"
        changed = True
    translation_count = len(re.findall(rf"(?<!\S){re.escape(TRANSLATION_PACKAGE)}(?=\s|$)", block))
    if translation_count > 1:
        raise ValueError(f"Expected at most one {TRANSLATION_PACKAGE}, found {translation_count}")
    if translation_count and EMBEDDED_TRANSLATION in ui_recipe:
        block = re.sub(rf"(?<!\S){re.escape(TRANSLATION_PACKAGE)}(?=\s|$)", "", block)
        changed = True
    if not changed:
        return False
    image.write_text(text[:blocks[0].start()] + block + text[blocks[0].end():], encoding="utf-8", newline="\n")
    return True


def build(source, wrt, target_dir):
    source, wrt, target_dir = source.resolve(), wrt.resolve(), target_dir.resolve()
    core = source / "athena-led"
    makefile = core / "Makefile"
    recipe = makefile.read_text(encoding="utf-8")
    ui = ui_recipe(source)
    cargo = tomllib.loads((core / "Cargo.toml").read_text(encoding="utf-8"))
    version = cargo["package"]["version"]
    if make_value(recipe, "PKG_VERSION") != version or make_value(ui, "PKG_VERSION") != version:
        raise ValueError("Athena Cargo, core package and LuCI versions must match")
    lock_hash = hashlib.sha256((core / "Cargo.lock").read_bytes()).hexdigest()
    revision = output("git", "rev-parse", "HEAD", cwd=source)
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full Git commit ID")
    # Check the packaging contract before spending time on Rust compilation.
    for key in ("PKG_SOURCE", "PKG_SOURCE_URL", "PKG_HASH"):
        make_value(recipe, key)
    adapt_device_packages(wrt, ui)
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
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("source", type=Path)
    prepare_parser.add_argument("wrt", type=Path)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("source", type=Path)
    build_parser.add_argument("wrt", type=Path)
    build_parser.add_argument("target_dir", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        adapt_device_packages(args.wrt.resolve(), ui_recipe(args.source))
    else:
        build(args.source, args.wrt, args.target_dir)
