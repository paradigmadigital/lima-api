from string import Template

BASE_CLASS = Template("""
class ${model_class_name}(${model_class_parent}):
${class_attributes}
${class_methods}
""")

LIMA_FUNCTION = Template("""
    @lima_api.${method}(
        path="${path}",
        default_response_code=${default_response_code},
        response_mapping=${response_mapping},
        headers=${headers},
        default_exception=${default_exception},
    )
    def ${function_name}(
        self,
        ${function_params}
    ) -> ${function_return}:
        ...
""")

BASE_PARAM = Template("""
        ${param_name}: ${param_type} = ${param_field}(${param_kwargs}),""")
