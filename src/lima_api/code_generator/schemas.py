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
    ENUM = "enum"
    UNION = "union"
    CONST = "const"


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
        self.models = set()

    def _get_final_type(self, obj):
        def_type = None
        if "$ref" in obj:
            ref = self.parser.get_ref(obj.get("$ref"))
            def_type = ref.name
            self.models.add(ref.name)
            self.models.update(ref.models)

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
                    self.models.add(ref.name)
                    self.models.update(ref.models)
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
                                self.models.add(ref.name)
                                self.models.update(ref.models)
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
                            self.models.add(obj.name)
                            self.models.update(obj.models)
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
            self.models.add(ref.name)
            self.models.update(ref.models)
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
        self.models = set()

    def __str__(self):
        return self._str

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def set_as_object(self, properties: dict, required: Optional[list] = None) -> None:
        self.type = SchemaObjectType.OBJECT
        self.name = snake_to_camel(self.name)
        self.models.add(self.name)
        if required is None:
            required = []

        props: list[PropertyParser] = []
        for prop, definition in properties.items():
            parser = PropertyParser(self.parser, prop, definition, is_required=prop in required)
            parser.parse()
            self.models.update(parser.models)
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
        self.attributes = alias_type
        self._str = f"\n{self.name}: typing.TypeAlias = {alias_type}\n"

    def set_as_array(self, array_type: str, required=False) -> None:
        self.type = SchemaObjectType.ARRAY
        if required:
            self._str = f"typing.Optional[list[{array_type}]] = None"
        else:
            self._str = f"list[{array_type}]"

    def set_as_enum(self, type_name, options: list[Any], enum_type: OpenApiType):
        self.type = SchemaObjectType.ENUM
        self.models.add(type_name)
        self._str = str(EnumObject(type_name, options, enum_type))

    def set_as_const(self, value):
        self.type = SchemaObjectType.CONST
        self._str = f"Literal[{value}]"

    def set_as_union(self, items):
        self.type = SchemaObjectType.UNION
        options: set[str] = set()
        for any_of in items:
            if "$ref" in any_of:
                ref = self.parser.get_ref(any_of["$ref"])
                self.models.add(ref.name)
                options.add(ref.name)
            elif "items" in any_of:
                ops = []
                if "$ref" in any_of["items"]:
                    ref = self.parser.get_ref(any_of["$ref"])
                    self.models.add(ref.name)
                    ops.append(ref.name)
                elif any_of["items"].get("type") in OPENAPI_2_TYPE_MAPPING:
                    ops.append(OPENAPI_2_TYPE_MAPPING[any_of["items"]["type"]])
                else:
                    raise NotImplementedError("Not supported type")
                options.add(f"list[{', '.join(ops)}]")
            elif any_of.get("type") in OPENAPI_2_TYPE_MAPPING:
                some_type = OPENAPI_2_TYPE_MAPPING[any_of.get("type")]
                options.add(some_type)
            else:
                # Add on embed_cls
                raise NotImplementedError("not supported")
        self._str = f"typing.Union[{', '.join(options)}]" if len(options) > 1 else options.pop()


class SchemaParser:
    def __init__(self, schemas: dict[str, dict], base_name: str = "#/components/schemas/"):
        self.raw_schemas: dict[str, dict] = schemas
        self.base_name: str = base_name
        self.schemas: dict[str, SchemaObject] = {}
        self.order: list[str] = []
        self.models = set()

    def parse(self):
        if self.schemas:
            return
        for name in self.raw_schemas:
            self.get_ref(f"{self.base_name}{name}")

    def process_schema(self, schema_name: str, schema_data: dict) -> SchemaObject:
        if {"not", "oneOf"}.intersection(schema_data.keys()):
            raise NotImplementedError("Not implemented")

        if "anyOf" in schema_data:
            new_schema = SchemaObject(self, schema_name)
            new_schema.set_as_union(schema_data.get("anyOf", []))
            self.models.update(new_schema.models)
            return new_schema

        if "allOf" in schema_data:
            new_schema = SchemaObject(self, schema_name)
            for item in schema_data.get("allOf", []):
                schema = self.process_schema(schema_name, item)
                self.models.update(new_schema.models)
                new_schema.attributes += schema.attributes
            new_schema.set_as_object({}, [])
            self.models.update(new_schema.models)
            return new_schema

        if "properties" in schema_data and "type" not in schema_data:
            schema_data["type"] = "object"

        new_schema = SchemaObject(self, schema_name)
        match schema_data.get("type"):
            case "object":
                new_schema.set_as_object(
                    properties=schema_data.get("properties") or {},
                    required=schema_data.get("required"),
                )
                self.models.update(new_schema.models)
            case "array":
                items = schema_data.get("items", {})
                array_type = items.get("type")
                if array_type in OPENAPI_2_TYPE_MAPPING:
                    new_schema.set_as_alias(f"list[{OPENAPI_2_TYPE_MAPPING.get(array_type)}]")
                elif "$ref" in items:
                    obj = self.get_ref(items.get("$ref"))
                    self.models.add(obj.name)
                    self.models.update(obj.models)
                    new_schema.set_as_alias(f"list[{obj.name}]")
                else:
                    raise NotImplementedError(f"Type for list {array_type} not supported")
            case "string":
                if "enum" in schema_data:
                    new_schema.set_as_enum(schema_name, schema_data.get("enum"), schema_data.get("type"))
                    self.models.update(new_schema.models)
                    return new_schema
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                raise NotImplementedError(f"Type {schema_data.get('type')} not supported")
            case _:
                if "$ref" in schema_data:
                    obj = self.get_ref(schema_data.get("$ref"))
                    self.models.add(obj.name)
                    self.models.update(obj.models)
                    return obj
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
