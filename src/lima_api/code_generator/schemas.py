from enum import Enum
from typing import Any, Optional

from lima_api.code_generator.templates import BASE_CLASS
from lima_api.code_generator.utils import (
    OPENAPI_2_TYPE_MAPPING,
    OpenApiType,
    camel_to_snake,
    snake_to_camel,
)


class EnumObject:
    def __init__(self, type_name, options: list[Any], enum_type: OpenApiType) -> None:
        self.name: str = type_name
        self.type: OpenApiType = enum_type
        self.options = options

    def __str__(self):
        attributes = ""
        for choice in self.options:
            key = f"OP_{choice}"
            if self.type == OpenApiType.STRING:
                key = camel_to_snake(choice)
            attributes += f'    {key.upper()} = "{choice}"\n'
        return BASE_CLASS.substitute(
            model_class_name=self.name,
            model_class_parent=f"{OPENAPI_2_TYPE_MAPPING.get(self.type)}, Enum",
            class_attributes=attributes,
            class_methods="",
        ).replace("\n\n", "\n")


class SchemaObjectType(str, Enum):
    OBJECT = "object"
    ALIAS = "alias"
    ARRAY = "array"


class PropertyParser:
    def __init__(self, parser: "SchemaParser", name: str, definition: dict, is_required=False):
        self.name: str = name
        self.type: str = ""
        self.parser: SchemaParser = parser
        self.definition: dict = definition
        self.is_required: bool = is_required
        self._str: str = ""
        self.enum: Optional[EnumObject] = None
        self.embed_cls: Optional[SchemaObject] = None

    def _get_final_type(self, obj):
        def_type = None
        if "$ref" in obj:
            ref = self.parser.get_ref(obj.get("$ref"))
            def_type = ref.name

        return def_type

    def parse(self):
        def_type = self.definition.get("type")
        if def_type in OPENAPI_2_TYPE_MAPPING:
            def_type: str = OPENAPI_2_TYPE_MAPPING.get(def_type)
            if "items" in self.definition:
                items = self.definition.get("items")
                item_type = items.get("type")
                if "$ref" in items:
                    ref = self.parser.get_ref(items.get("$ref"))
                    def_type = f"{def_type}[{ref.name}]"
                else:
                    is_list = False
                    item_type = OPENAPI_2_TYPE_MAPPING.get(item_type)
                    if "anyOf" in items or "oneOf" in items:
                        key_of = "anyOf" if "anyOf" in items else "oneOf"
                        any_of = []
                        for item in items[key_of]:
                            if "$ref" in item:
                                ref = self.parser.get_ref(item.get("$ref"))
                                any_of.append(ref.name)
                            elif item.get("type") in OPENAPI_2_TYPE_MAPPING:
                                item_type = OPENAPI_2_TYPE_MAPPING.get(item.get("type"))
                                any_of.append(item_type)
                            else:
                                raise NotImplementedError(f"Unsupported type {item.get('type')}")
                        item_type = ", ".join(any_of)
                        if def_type == "list":
                            is_list = True
                        def_type = "typing.Union"
                    elif item_type is None:
                        if "properties" in items:
                            item_type = snake_to_camel(self.name) + "Embed"
                            obj = SchemaObject(self.parser, item_type)
                            obj.set_as_object(items.get("properties"), items.get("required", []))
                            self.embed_cls = obj
                        else:
                            raise NotImplementedError("Unsupported jet")

                    def_type = f"{def_type}[{item_type}]"
                    if is_list:
                        def_type = f"list[{def_type}]"

            if "enum" in self.definition:
                type_name = snake_to_camel(self.definition.get("title", self.name))
                self.enum = EnumObject(
                    type_name=type_name,
                    options=self.definition.get("enum"),
                    enum_type=self.definition.get("type"),
                )
                def_type = type_name
        if "$ref" in self.definition:
            ref = self.parser.get_ref(self.definition.get("$ref"))
            def_type = ref.name
        field_kwargs = ""
        field_name = camel_to_snake(self.name)
        kwargs = []
        if field_name != self.name:
            kwargs.append(f'        alias="{self.name}",\n')
        for key in ["title", "description"]:
            value = self.definition.get(key, None)
            if value is None:
                continue
            if isinstance(value, str):
                kwargs.append(f'        {key}="{value}",\n')
            else:
                kwargs.append(f"        {key}={value},\n")
        if kwargs:
            field_kwargs += "\n"
            field_kwargs += "".join(kwargs)
            field_kwargs += "    "
        self.type = def_type
        self._str = f"{field_name}: {def_type} = " f"pydantic.Field({field_kwargs})"

    def __str__(self):
        return self._str


class SchemaObject:
    def __init__(self, parser: "SchemaParser", name: str):
        self.name: str = name
        self.parser: SchemaParser = parser
        self.type: Optional[SchemaObjectType] = None
        self._str: str = ""
        self.enums: list[EnumObject] = []
        self.embed_cls: list[SchemaObject] = []
        self.attributes: str = ""

    def __str__(self):
        return self._str

    def set_as_object(self, properties: dict, required: Optional[list] = None) -> None:
        self.type = SchemaObjectType.OBJECT
        self.name = snake_to_camel(self.name)
        if required is None:
            required = []

        props: list[PropertyParser] = []
        for prop, definition in properties.items():
            parser = PropertyParser(self.parser, prop, definition, is_required=prop in required)
            parser.parse()
            if parser.enum:
                self.enums.append(parser.enum)
            props.append(parser)
            if parser.embed_cls is not None:
                self.embed_cls.append(parser.embed_cls)
            self.attributes += f"\n    {parser}"
        self._str += "".join([str(enum) for enum in self.enums])
        self._str += "\n\n".join([str(cls) for cls in self.embed_cls])
        if self.embed_cls:
            self._str += "\n"
        self._str += BASE_CLASS.substitute(
            model_class_name=self.name,
            model_class_parent="pydantic.BaseModel",
            class_attributes=self.attributes,
            class_methods="",
        ).replace("\n\n", "\n")

    def set_as_alias(self, alias_type: str) -> None:
        self.type = SchemaObjectType.ALIAS
        self.name = snake_to_camel(self.name)
        self._str = f"\n{self.name}: typing.TypeAlias = {alias_type}\n"

    def set_as_array(self, array_type: str, required=False) -> None:
        self.type = SchemaObjectType.ARRAY
        if required:
            self._str = f"typing.Optional[list[{array_type}]] = None"
        else:
            self._str = f"list[{array_type}]"


class SchemaParser:
    def __init__(self, schemas: dict[str, dict], base_name: str = "#/components/schemas/"):
        self.raw_schemas: dict[str, dict] = schemas
        self.base_name: str = base_name
        self.schemas: dict[str, SchemaObject] = {}
        self.order: list[str] = []

    def parse(self):
        if self.schemas:
            return
        for name in self.raw_schemas:
            self.get_ref(f"{self.base_name}{name}")

    def process_schema(self, schema_name: str, schema_data: dict) -> SchemaObject:
        if {"not", "anyOf", "oneOf"}.intersection(schema_data.keys()):
            raise NotImplementedError("Not implemented")

        if "allOf" in schema_data:
            new_schema = SchemaObject(self, schema_name)
            for item in schema_data.get("allOf", []):
                schema = self.process_schema(schema_name, item)
                new_schema.attributes += schema.attributes
            new_schema.set_as_object({}, [])
            return new_schema

        if "properties" in schema_data and "type" not in schema_data:
            schema_data["type"] = "object"

        new_schema = SchemaObject(self, schema_name)
        match schema_data.get("type"):
            case "object":
                new_schema.set_as_object(
                    properties=schema_data.get("properties"),
                    required=schema_data.get("required"),
                )
            case "array":
                items = schema_data.get("items", {})
                array_type = items.get("type")
                if array_type in OPENAPI_2_TYPE_MAPPING:
                    new_schema.set_as_alias(f"list[{OPENAPI_2_TYPE_MAPPING.get(array_type)}]")
                elif "$ref" in items:
                    obj = self.get_ref(items.get("$ref"))
                    new_schema.set_as_alias(f"list[{obj.name}]")
                else:
                    raise NotImplementedError(f"Type for list {array_type} not supported")
            case _:
                if "$ref" in schema_data:
                    return self.get_ref(schema_data.get("$ref"))
                raise NotImplementedError(f"Type {schema_data.get('type')} not supported")
        return new_schema

    def get_ref(self, ref: str) -> SchemaObject:
        if ref not in self.schemas:
            schema_name = ref.replace(self.base_name, "")
            if schema_name not in self.raw_schemas:
                raise ValueError(f"Schema {ref} not found")

            self.schemas[ref] = self.process_schema(schema_name, self.raw_schemas[schema_name])
            self.order.append(ref)
        return self.schemas[ref]

    def print(self, file=None):
        for schema_name in self.order:
            print(self.schemas.get(schema_name), file=file)
