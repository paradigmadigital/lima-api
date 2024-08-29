import argparse
import json
import os
from io import StringIO

from lima_api.code_generator.schemas import SchemaParser
from lima_api.code_generator.utils import camel_to_snake


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

    api_title = camel_to_snake(openapi_content.get("info", {}).get("title", ""))
    servers = openapi_content.get("servers", [])
    server = "http://localhost/"
    if servers:
        server = server[0]

    schema_parse: SchemaParser = generate_models(openapi_content)
    model_content: StringIO = StringIO()
    schema_parse.print(file=model_content)
    model_content.seek(0)
    model_content: str = model_content.read()
    if "pydantic" in model_content:
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
    for path, path_data in paths.items():
        for method, method_data in path_data.items():
            #print(method_data)
            for param in method_data.get("parameters", []):
                ...
            for status, data in method_data.get("responses", {}).items():
                ...


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    options = parser.parse_args()
    gen_from_file(options.file)


if __name__ == "__main__":
    main()
