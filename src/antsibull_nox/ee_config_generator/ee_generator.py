import os

import yaml
from jinja2 import Environment, FileSystemLoader

MATRIX_CONFIGS = [
    {
        "name": "ansible-core devel @ RHEL UBI 9",
        "ansible_core": "https://github.com/ansible/ansible/archive/devel.tar.gz",
        "ansible_runner": "ansible-runner",
        "other_deps": {
            "python_interpreter": {
                "package_system": (
                    "python3.11 python3.11-pip "
                    "python3.11-wheel python3.11-cryptography"
                ),
                "python_path": "/usr/bin/python3.11",
            }
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
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_requirements_file(self, output_path, collection_filename):
        req_config = {
            "collections": [{"name": f"src/{collection_filename}", "type": "file"}]
        }

        req_filename = os.path.join(output_path, "requirements.yml")
        with open(req_filename, "w", encoding="utf-8") as f:
            yaml.dump(req_config, f)

        return req_filename

    def generate_execution_environments(
        self, output_path, collection_filename, configs=None
    ):
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
