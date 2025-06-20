# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025, Ansible Project

"""
Generate execution environment definitions from templates.
"""

import os

from antsibull_fileutils.yaml import store_yaml_file
from jinja2 import Environment, FileSystemLoader

MATRIX_CONFIGS = [
    {
        "name": "ansible-core devel @ RHEL UBI 9",
        "ansible_core": "https://github.com/ansible/ansible/archive/devel.tar.gz",
        "ansible_runner": "ansible-runner",
        "other_deps": {},
        "python_interpreter": {
            "package_system": (
                "python3.11 python3.11-pip " "python3.11-wheel python3.11-cryptography"
            ),
            "python_path": "/usr/bin/python3.11",
        },
        "base_image": "docker.io/redhat/ubi9:latest",
        "pre_base": "RUN echo 'No prepend actions'",
    },
    {
        "name": "ansible-core 2.15 @ Rocky Linux 9",
        "ansible_core": "https://github.com/ansible/ansible/archive/stable-2.15.tar.gz",
        "ansible_runner": "ansible-runner",
        "other_deps": {},
        "base_image": "quay.io/rockylinux/rockylinux:9",
        "pre_base": "RUN echo 'No prepend actions'",
    },
]


class ExecutionEnvironmentGenerator:
    """
    Generate execution environment files from Jinja2 templates.
    """

    def __init__(self):
        """
        Initialize the EE generator.
        """
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_requirements_file(self, output_path, collection_filename):
        """
        Generate a requirements.yml file for collection dependencies.

        Args:
            output_path: Directory for requirements.yml
            collection_filename: Name of the collection tarball

        Returns:
            Path to the generated requirements.yml file
        """
        req_config = {
            "collections": [{"name": f"src/{collection_filename}", "type": "file"}]
        }

        req_filename = os.path.join(output_path, "requirements.yml")
        store_yaml_file(req_filename, req_config)

        return req_filename

    def generate_execution_environments(
        self, output_path, collection_filename, configs=None
    ):
        """
        Generate execution environment definitions from the config matrix.

        Args:
            output_path: Directory for EE yml files
            collection_filename: Name of the collection tarball
            configs: List of matrix configs

        Returns:
            Generated EE yml file paths
        """
        if configs is None:
            configs = MATRIX_CONFIGS

        template = self.env.get_template("execution-environment.j2")
        generated_files = []

        for matrix in configs:
            context = {
                "ansible_core": matrix["ansible_core"],
                "ansible_runner": matrix["ansible_runner"],
                "base_image": matrix["base_image"],
                "pre_base": matrix["pre_base"],
                "collection_filename": collection_filename,
                "other_deps": matrix.get("other_deps", {}),
                "python_interpreter": matrix.get("python_interpreter"),
            }

            output = template.render(**context)

            config_name = matrix["name"].replace(" @ ", "_").replace(" ", "_").lower()
            ee_filename = os.path.join(
                output_path, f"execution-environment-{config_name}.yml"
            )

            with open(ee_filename, "w", encoding="utf-8") as f:
                f.write(output)

            generated_files.append(ee_filename)

        return generated_files
