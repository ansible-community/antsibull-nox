# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Build execution environments for testing.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
from pathlib import Path
from typing import Optional

import yaml

from antsibull_nox.ee_config_generator import ExecutionEnvironmentGenerator


@dataclasses.dataclass()
class Args:
    path: Path
    namespace: Optional[str] = None
    name: Optional[str] = None


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", help="path to collection", type=Path)
    parser.add_argument("-s", "--namespace", help="collection namespace")
    parser.add_argument("-n", "--name", help="collection name")
    return parser.parse_args()


def check_galaxy_version(args: Args):
    if args.path and not os.path.exists(args.path):
        print(f"Path {args.path} not found")

    galaxy_path = args.path / "galaxy.yml"

    with open(galaxy_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)

    config["version"] = config.get("version") or "0.0.1"

    with open(galaxy_path, "wb") as f:
        f.write(yaml.dump(config).encode("utf-8"))

    return config


def build_collection(args: Args, version: str):

    collection_path = args.path
    collection_namespace = args.namespace
    collection_name = args.name
    output_path = args.path

    try:

        cmd = [
            "ansible-galaxy",
            "collection",
            "build",
            "--output-path",
            str(output_path),
        ]

        working_dir = os.getcwd()
        os.chdir(collection_path)

        subprocess.run(cmd, check=True)

        os.chdir(working_dir)

        collection_filename = (
            f"{collection_namespace}-{collection_name}-{version}.tar.gz"
        )

        return Path(output_path) / collection_filename

    except subprocess.CalledProcessError as e:
        print(f"An error was encountered while building the collection: {e}")
        return None
    except OSError as e:
        print(f"An error was encountered while building the collection: {e}")
        return None


def build_ee_image(args: Args):

    built_images = []

    ee_files = list(args.path.glob("execution-environment-*.yml"))

    for ee_file in ee_files:
        prefix = "execution-environment-"
        image_name = f"{args.namespace}-{args.name}-{ee_file.stem.replace(prefix, '')}"

        try:
            context_dir = str(ee_file.parent / f"context-{ee_file.stem}")

            cmd = [
                "ansible-builder",
                "build",
                "--file",
                str(ee_file),
                "--tag",
                image_name,
                "--container-runtime",
                "podman",
                "--verbosity",
                "3",
                "--context",
                context_dir,
            ]

            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            if result.returncode == 0:
                built_images.append(image_name)
            else:
                print(
                    f"Could not build image for {ee_file}, return code: {result.returncode}"
                )

        except OSError as e:
            print(
                f"An error was encountered while building an image for {ee_file}: {e}"
            )

    return built_images


def main():
    """
    Main execution function.
    """
    parsed_args = parse_arguments()

    args = Args(
        path=parsed_args.path,
        namespace=parsed_args.namespace,
        name=parsed_args.name,
    )
    config = check_galaxy_version(args)

    collection_tarball = build_collection(args, config["version"])

    ee_generator = ExecutionEnvironmentGenerator()

    ee_generator.generate_requirements_file(args.path, collection_tarball.name)

    ee_generator.generate_execution_environments(args.path, collection_tarball.name)

    build_ee_image(args)


if __name__ == "__main__":
    main()
