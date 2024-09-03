import argparse
import json
import os
from io import StringIO

from lima_api.code_generator.cli_gen import ClientGenerator
from lima_api.code_generator.schemas import SchemaParser


def generate_models(openapi_content: dict) -> SchemaParser:
    components = openapi_content.get("components", {})
    schema_parse = SchemaParser(components.get("schemas", {}))
    schema_parse.parse()
    return schema_parse


def gen_from_file(file_path):
    with open(file_path) as f:
        openapi_content = json.load(f)

    base_name: str = os.path.basename(file_path).replace(".json", "")
    base_dir = os.path.join(os.path.dirname(file_path), base_name)
    if not os.path.isdir(base_dir):
        os.mkdir(base_dir)

    api_title = openapi_content.get("info", {}).get("title", "")
    servers = openapi_content.get("servers", [])
    server = "http://localhost/"
    if servers and isinstance(servers, (list, tuple)):
        server = servers[0].get("url")
        if servers[0].get("variables", {}):
            vars = {key: value.get("default") for key, value in servers[0]["variables"].items()}
            for key, value in vars.items():
                server = server.replace("{" + key + "}", value)
    elif servers:
        server = servers

    schema_parse: SchemaParser = generate_models(openapi_content)
    model_content: StringIO = StringIO()
    schema_parse.print(file=model_content)
    model_content.seek(0)
    model_content: str = model_content.read()
    has_model = False
    if "pydantic" in model_content:
        has_model = True
        with open(os.path.join(base_dir, "models.py"), "w") as f:
            add_enter = False
            if "typing" in model_content:
                f.write("import typing\n")
                add_enter = True
            if "Enum" in model_content:
                f.write("from enum import Enum\n")
                add_enter = True
            if add_enter:
                f.write("\n")

            f.write("import pydantic\n\n")
            f.write(model_content)

    paths = openapi_content.get("paths", {})
    generator = ClientGenerator(schema_parse, paths)
    generator.parse()
    client_content: str = str(generator)
    with open(os.path.join(base_dir, "client.py"), "w") as f:
        f.write(f"#\n# Client auto generated for {api_title}\n#\n")
        add_enter = False
        if "typing" in client_content:
            f.write("import typing\n")
            add_enter = True
        if "Enum" in client_content:
            f.write("from enum import Enum\n")
            add_enter = True
        if add_enter:
            f.write("\n")

        f.write("import lima_api\n")
        if "pydantic" in client_content:
            f.write("import pydantic\n")
        f.write("\n")
        if has_model:
            f.write("from .models import (")
            for model in sorted(generator.models):
                f.write(f"\n    {model},")
            f.write("\n)\n\n")
        f.write(client_content)
        f.write(f'\nclient = ApiClient(base_url="{server}")\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    options = parser.parse_args()
    gen_from_file(options.file)


if __name__ == "__main__":
    main()
