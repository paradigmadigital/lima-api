import re
from typing import Optional

from lima_api.code_generator.schemas import (
    SchemaObject,
    SchemaObjectType,
    SchemaParser,
)
from lima_api.code_generator.templates import (
    BASE_CLASS,
    BASE_PARAM,
    LIMA_FUNCTION,
)
from lima_api.code_generator.utils import (
    OPENAPI_2_TYPE_MAPPING,
    camel_to_snake,
    snake_to_camel,
)

STAR_WITH_NUMBER = re.compile("^[0-9]+")
PARAM_MAPPING = {
    "path": "lima_api.PathParameter",
    "query": "lima_api.QueryParameter",
    "header": "lima_api.HeaderParameter",
    # "cookie": "",  # Not supported
}


class LimaExceptionGenerator:
    def __init__(self, name: str, details: str, model: Optional[str] = None):
        self.name: str = snake_to_camel(name)
        self.details: str = details
        self.model: Optional[str] = model

    def __str__(self):
        class_attributes = f'    detail: str = "{self.details}"'
        class_methods = ""
        if self.model:
            class_methods = f"    model = {self.model}"
        return BASE_CLASS.substitute(
            model_class_name=self.name,
            model_class_parent="lima_api.LimaException",
            class_attributes=class_attributes,
            class_methods=class_methods,
        )

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class LimaFunction:
    def __init__(self, client_generator: "ClientGenerator", method: str, path: str, spec: dict):
        self.client_generator: ClientGenerator = client_generator
        self.method: str = method.lower()
        self.path: str = path
        self.spec: dict = spec
        self._default_status: Optional[int] = None
        self._default_response: Optional[str] = None
        self._str = ""
        self._exceptions: list[LimaExceptionGenerator] = []
        self._embed_cls: list[SchemaObject] = []

    @property
    def name(self) -> str:
        funct_name = f"{self.method}_{camel_to_snake(self.path)}"
        if "operationId" in self.spec:
            funct_name = camel_to_snake(self.spec.get("operationId"))
        # TODO generate name
        return funct_name

    @property
    def _parameters(self) -> list[dict]:
        return self.spec.get("parameters", [])

    @property
    def params(self) -> str:
        params = ""

        request_body: dict = self.spec.get("requestBody", {}).get("content", {})
        content: dict = request_body.get("application/json") or {}

        if content:
            obj = self.client_generator.process_schema("", content.get("schema"))
            params += BASE_PARAM.substitute(
                param_name="body",
                param_type=obj.name,
                param_field="lima_api.BodyParameter",
                param_kwargs="",
            )

        for param in self._parameters:
            param_kwargs = []
            param_field = PARAM_MAPPING.get(param.get("in"))
            if param_field is None:
                continue

            param_type = OPENAPI_2_TYPE_MAPPING.get(param.get("schema", {}).get("type"))
            if not param_type:
                raise NotImplementedError("Invalid type for parameter")

            alias = param.get("name")
            param_name = camel_to_snake(alias)
            if alias != param_name:
                param_kwargs.append(f'alias="{alias}"')

            default = param.get("default")
            if default:
                param_kwargs.append(f"default={default}")

            params += BASE_PARAM.substitute(
                param_name=param_name,
                param_type=param_type,
                param_field=param_field,
                param_kwargs=", ".join(param_kwargs),
            )
            ...
        if params:
            params = "*," + params
        return params

    @property
    def headers(self) -> str:
        return "{}"

    @property
    def _responses(self) -> dict:
        return self.spec.get("responses", {})

    @property
    def returned_type(self) -> str:
        return self._get_type(str(self.default_response_code))

    def _get_type(self, status: str) -> str:
        returned_type = "bytes"
        if status in self._responses:
            content = self._responses[status].get("content", {})
            if not content:
                returned_type = "None"
            elif "application/json" in content:
                schema = content.get("application/json").get("schema")
                if not schema:
                    returned_type = "dict"
                elif "anyOf" in schema:
                    options: set[str] = set()
                    for any_of in schema["anyOf"]:
                        if "$ref" in any_of:
                            ref = self.client_generator.get_ref(any_of["$ref"])
                            options.add(ref.name)
                        else:
                            # TODO generate model on fly
                            options.add("dict")
                    if len(options) > 1:
                        returned_type = f"typing.Union[{', '.join(options)}]"
                    else:
                        returned_type = options.pop()
                elif schema.get("type") in OPENAPI_2_TYPE_MAPPING:
                    returned_type = OPENAPI_2_TYPE_MAPPING[schema.get("type")]
                else:

                    candidate = self.client_generator.process_schema("", schema)
                    if candidate.name:
                        returned_type = candidate.name
                    elif candidate.type == SchemaObjectType.ALIAS:
                        _, returned_type = str(candidate).strip().rsplit(" = ", 1)
                    elif candidate.type == SchemaObjectType.OBJECT:
                        obj_name = snake_to_camel(schema.get("description", ""))
                        candidate = self.client_generator.process_schema(obj_name, schema)
                        if candidate.name:
                            self._embed_cls.append(candidate)
                        returned_type = candidate.name or "dict"
                    else:
                        raise NotImplementedError("Unexpected")
            elif "application/xml" in content or "text/plain" in content:
                returned_type = "str"
        return returned_type

    @property
    def default_response_code(self) -> int:
        if not self._default_status:
            codes = [int(status) for status in self._responses.keys() if status.isnumeric()]
            self._default_status = 200
            if len(codes) == 1:
                self._default_status = codes[0]
            elif codes:
                if "default" in self._responses.keys():
                    self._default_status = 200
                if 200 not in codes:
                    for status in sorted(codes):
                        if 200 >= status < 400:
                            self._default_status = status
                            break
                    else:
                        self._default_status = codes[0]
        return self._default_status

    @property
    def response_mapping(self) -> dict[int, LimaExceptionGenerator]:
        mapping = {}
        for status in self._responses.keys():
            if status == "default":
                continue
            int_status = int(status)
            if int_status != self.default_response_code:
                details = self.spec["responses"][status].get("description")
                model_type = self._get_type(status)
                if model_type in ["dict", "list"]:
                    model_type = "None"
                exception_name = model_type if model_type != "None" else details

                if "[" in exception_name:
                    exception_name = details

                numbers = STAR_WITH_NUMBER.match(exception_name)
                if numbers:
                    number = numbers.group()
                    exception_name = exception_name[len(number) :] + number

                low_ex = exception_name.lower()
                if not any(word in low_ex for word in ["error", "invalid", "exception"]):
                    exception_name += "Error"

                lima_exception = LimaExceptionGenerator(
                    name=exception_name,
                    details=details,
                    model=model_type,
                )
                self._exceptions.append(lima_exception)
                mapping[int_status] = lima_exception
        return mapping

    def __str__(self) -> str:
        response_mapping: str = "{"
        if self.response_mapping:
            for code, ex in self.response_mapping.items():
                response_mapping += f"\n            {code}: {ex.name},"
            response_mapping += "\n        }"
        else:
            response_mapping += "}"

        self._str += LIMA_FUNCTION.substitute(
            method=self.method,
            path=self.path,
            default_response_code=self.default_response_code,
            response_mapping=response_mapping,
            headers=self.headers,
            default_exception="lima_api.LimaException",
            function_name=self.name,
            function_params=self.params,
            function_return=self.returned_type,
        )
        return self._str


class ClientGenerator:
    def __init__(self, schema_parser: SchemaParser, paths: dict):
        self.schema_parser: SchemaParser = schema_parser
        self.paths: dict = paths
        self._str = ""

    def __str__(self) -> str:
        return self._str

    def get_ref(self, ref: str) -> SchemaObject:
        return self.schema_parser.get_ref(ref)

    def process_schema(self, schema_name: str, schema_data: dict) -> SchemaObject:
        return self.schema_parser.process_schema(schema_name, schema_data)

    def parse(self):
        exceptions = set()
        embed_cls = set()
        class_attributes = "    response_mapping = {}"
        class_methods = ""
        for path, methods in self.paths.items():
            for method, data in methods.items():
                funct = LimaFunction(self.schema_parser, method, path, data)
                class_methods += str(funct)
                exceptions.update(funct._exceptions)
                embed_cls.update(funct._embed_cls)

        self._str = BASE_CLASS.substitute(
            model_class_name="ApiClient",
            model_class_parent="lima_api.SyncLimaApi",
            class_attributes=class_attributes,
            class_methods=class_methods,
        )
        _str = "\n".join(str(ex) for ex in exceptions)
        if exceptions:
            _str += "\n"
        _str += "\n".join(str(model) for model in embed_cls)
        if embed_cls:
            _str += "\n"
        self._str = _str + self._str
