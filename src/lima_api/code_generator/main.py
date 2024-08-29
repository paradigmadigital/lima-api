import argparse
import json
import os

from lima_api.code_generator.schemas import SchemaParser
from lima_api.code_generator.utils import camel_to_snake


def generate_models(openapi_content: dict) -> SchemaParser:
    components = openapi_content.get("components", {})
    schema_parse = SchemaParser(components.get("schemas", {}))
    schema_parse.parse()
    return schema_parse


def gen_from_file(file_obj):
    with open(file_obj) as f:
        openapi_content = json.load(f)

    api_title = camel_to_snake(openapi_content.get("info", {}).get("title", ""))
    servers = openapi_content.get("servers", [])
    server = "http://localhost/"
    if servers:
        server = server[0]

    schema_parse: SchemaParser = generate_models(openapi_content)
    schema_parse.print()

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
