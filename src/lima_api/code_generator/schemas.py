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
                if key[0].isdigit():
                    key = f"{camel_to_snake(self.name).upper()}_{key}"
            attributes += f'    {key.upper()} = "{choice}"\n'
        return (
            BASE_CLASS.substitute(
                model_class_name=self.name,
                model_class_parent=f"{OPENAPI_2_TYPE_MAPPING.get(self.type)}, Enum",
                class_attributes=attributes,
                class_methods="",
            )
            .replace("\n\n\n", "\n")
            .replace("\n\n", "\n")
        )

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class SchemaObjectType(str, Enum):
    OBJECT = "object"
    ALIAS = "alias"
    ARRAY = "array"
    ENUM = "enum"
    UNION = "union"
    CONST = "const"
    TYPE = "type"


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
        schema = self.parser.process_schema(snake_to_camel(self.name), self.definition)
        def_type = schema.attributes if schema.type != SchemaObjectType.OBJECT else schema.name
        self.models.update(schema.models)
        if schema.type == SchemaObjectType.ENUM:
            self.enum = schema
        elif schema.enums:
            self.enum = schema.enums.pop()
            schema.enums.add(self.enum)

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
        if "default" in self.definition:
            default_value = self.definition["default"]
            if isinstance(default_value, str):
                default_value = f'"{default_value}"'
            kwargs.append(f"        default={default_value},\n")
        elif "Optional" in def_type:
            kwargs.append("        default=None,\n")
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
        self.enums: set[EnumObject] = set()
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
                self.enums.add(parser.enum)
            props.append(parser)
            if parser.embed_cls is not None:
                self.embed_cls.append(parser.embed_cls)
            self.attributes += f"\n    {parser}"
        if not properties and not self.attributes:
            self.attributes = "    ..."
        # self._str += "".join([str(enum) for enum in self.enums])
        self._str += "\n\n".join([str(cls) for cls in self.embed_cls])
        if self.embed_cls:
            self._str += "\n"
        self._str += (
            BASE_CLASS.substitute(
                model_class_name=self.name,
                model_class_parent="pydantic.BaseModel",
                class_attributes=self.attributes,
                class_methods="",
            )
            .replace("\n\n\n", "\n")
            .replace("\n\n", "\n")
        )

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
        self.attributes = self._str

    def set_as_enum(self, type_name, options: list[Any], enum_type: OpenApiType):
        self.type = SchemaObjectType.ENUM
        self.models.add(type_name)
        self._str = str(EnumObject(type_name, options, enum_type))
        self.attributes = type_name

    def set_as_const(self, value):
        self.type = SchemaObjectType.CONST
        if isinstance(value, str):
            value = f'"{value}"'
        self._str = f"typing.Literal[{value}]"
        self.attributes = self._str

    def set_as_union(self, items):
        self.type = SchemaObjectType.UNION
        options: set[str] = set()
        for any_of in items:
            if any_of == {}:
                options.add("dict")
            elif "$ref" in any_of:
                ref = self.parser.get_ref(any_of["$ref"])
                self.models.add(ref.name)
                options.add(ref.name)
            elif "const" in any_of:
                const = any_of["const"]
                if isinstance(const, str):
                    const = f'"{const}"'
                options.add(f"typing.Literal[{const}]")
            elif "items" in any_of:
                ops = []
                if "$ref" in any_of["items"]:
                    ref = self.parser.get_ref(any_of["items"]["$ref"])
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

        if len(options) == 1:
            self._str = options.pop()
        else:
            mode = "typing.Union"
            if "None" in options:
                options.remove("None")
                mode = "typing.Optional"
            self._str = f"{mode}[{', '.join(sorted(options))}]"
        self.attributes = self._str

    def set_as_type(self, std_type: str):
        self.type = SchemaObjectType.TYPE
        self._str = OPENAPI_2_TYPE_MAPPING[std_type]
        self.attributes = self._str


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
            if len(schema_data["allOf"]) == 1:
                new_schema = self.process_schema(schema_name, schema_data["allOf"][0])
                return new_schema
            else:
                for item in schema_data.get("allOf", []):
                    schema = self.process_schema(schema_name, item)
                    self.models.update(schema.models)
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
            case OpenApiType.ARRAY:
                items = schema_data.get("items", {})
                array_type = items.get("type")
                if array_type in OPENAPI_2_TYPE_MAPPING:
                    new_schema.set_as_alias(f"list[{OPENAPI_2_TYPE_MAPPING.get(array_type)}]")
                elif "$ref" in items:
                    obj = self.get_ref(items.get("$ref"))
                    self.models.add(obj.name)
                    self.models.update(obj.models)
                    new_schema.enums.update(obj.enums)
                    new_schema.models.update(obj.models)
                    new_schema.set_as_alias(f"list[{obj.name}]")
                elif "anyOf" in items:
                    obj = self.process_schema(schema_name, items)
                    new_schema.enums.update(obj.enums)
                    new_schema.models.update(obj.models)
                    self.models.update(obj.models)
                    new_schema.set_as_alias(f"list[{obj}]")
                else:
                    raise NotImplementedError(f"Type for list '{array_type}' not supported")
            case OpenApiType.BOOLEAN:
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                new_schema.set_as_type(schema_data.get("type"))
                return new_schema
            case OpenApiType.NUMBER:
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                new_schema.set_as_type(schema_data.get("type"))
                return new_schema
            case OpenApiType.INTEGER:
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                new_schema.set_as_type(schema_data.get("type"))
                return new_schema
            case OpenApiType.STRING:
                if "enum" in schema_data:
                    enums = schema_data.get("enum")
                    if len(enums) == 1:
                        new_schema.set_as_const(enums[0])
                        return new_schema
                    new_schema.set_as_enum(schema_name, enums, schema_data.get("type"))
                    self.models.update(new_schema.models)
                    return new_schema
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                new_schema.set_as_type(schema_data.get("type"))
                return new_schema
            case _:
                if "$ref" in schema_data:
                    obj = self.get_ref(schema_data.get("$ref"))
                    self.models.add(obj.name)
                    self.models.update(obj.models)
                    return obj
                if "const" in schema_data:
                    new_schema.set_as_const(schema_data.get("const"))
                    return new_schema
                raise NotImplementedError(f"Type {schema_data.get('type')} not supported")
        return new_schema

    def get_ref(self, ref: str) -> SchemaObject:
        if ref not in self.schemas:
            schema_name = ref.replace(self.base_name, "")
            if schema_name not in self.raw_schemas:
                raise ValueError(f"Schema {ref} not found")

            self.schemas[ref] = self.process_schema(schema_name, self.raw_schemas[schema_name])
            if self.base_name in ref and self.schemas[ref].type == SchemaObjectType.CONST:
                self.schemas[ref].set_as_alias(self.schemas[ref]._str)
            self.order.append(ref)
        return self.schemas[ref]

    def print(self, file=None):
        enums = set()
        for schema_name in self.order:
            schema = self.schemas.get(schema_name)
            enums_str = []
            for enum in schema.enums:
                if enum.name not in enums:
                    enums_str.append(str(enum))
                    enums.add(enum.name)

            if enums_str:
                print("\n".join(enums_str), file=file, end="\n")
            if schema.type == SchemaObjectType.ENUM:
                enums.add(schema.name)
            print(schema, file=file)
