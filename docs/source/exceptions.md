# Exceptions

Lima-API provides a comprehensive exception system that allows you to handle HTTP errors and validation issues in a structured way. All exceptions in Lima-API are built on top of the base `LimaException` class.

## Base Exception Classes

### LimaException

```{eval-rst}
.. autoclass:: lima_api.exceptions.LimaException
   :members:
   :undoc-members:
   :show-inheritance:
```

`LimaException` is the base exception class for all Lima-API exceptions. It provides rich information about HTTP requests and responses, making it easier to debug and handle errors.

#### Key Features

- **HTTP Context**: Access to the original HTTP request and response objects
- **Status Code**: Automatic extraction of HTTP status codes
- **Content Handling**: Built-in methods to parse response content as JSON or custom objects
- **Flexible Initialization**: Can be initialized with various combinations of parameters

#### Usage Examples

```python
import lima_api

try:
    # Your API call here
    result = await client.some_api_call()
except lima_api.LimaException as e:
    print(f"Status Code: {e.status_code}")
    print(f"Error Detail: {e.detail}")
    print(f"Response Content: {e.json()}")
    
    # Access the original HTTP objects
    if e.http_request:
        print(f"Request URL: {e.http_request.url}")
    if e.http_response:
        print(f"Response Headers: {e.http_response.headers}")
```

### ValidationError

```{eval-rst}
.. autoclass:: lima_api.exceptions.ValidationError
   :members:
   :undoc-members:
   :show-inheritance:
```

`ValidationError` is a specialized exception for handling validation errors that occur during request processing or response parsing.

#### Usage Examples

```python
import lima_api
from pydantic import ValidationError as PydanticValidationError

try:
    # API call that might have validation issues
    result = await client.create_user(invalid_data)
except lima_api.ValidationError as e:
    print(f"Validation failed: {e}")
    # The underlying pydantic error is available via __cause__
    if isinstance(e.__cause__, PydanticValidationError):
        for error in e.__cause__.errors():
            print(f"Field: {error['loc']}, Error: {error['msg']}")
```

## Exception Handling Patterns

### Response Mapping

Lima-API allows you to map specific HTTP status codes to custom exception classes using the `response_mapping` feature:

```python
import lima_api

class CustomNotFoundError(lima_api.LimaException):
    detail = "Resource not found"

class CustomAuthError(lima_api.LimaException):
    detail = "Authentication failed"

class MyApiClient(lima_api.LimaApi):
    base_url = "https://api.example.com"
    response_mapping = {
        404: CustomNotFoundError,
        401: CustomAuthError,
    }

    @lima_api.get("/users/{user_id}")
    async def get_user(self, user_id: int) -> dict:
        pass

# Usage
with MyApiClient() as client:
    try:
        user = await client.get_user(999)
    except CustomNotFoundError:
        print("User not found!")
    except CustomAuthError:
        print("Authentication required!")
```

### Method-Level Exception Mapping

You can also define response mapping at the method level:

```python
@lima_api.get(
    "/sensitive-data",
    response_mapping={
        403: CustomPermissionError,
        429: CustomRateLimitError,
    }
)
async def get_sensitive_data(self) -> dict:
    pass
```

### Global Exception Handling

For global exception handling, you can catch the base `LimaException`:

```python
async def safe_api_call():
    try:
        return await client.some_method()
    except lima_api.LimaException as e:
        # Log the error with full context
        logger.error(
            "API call failed",
            extra={
                "status_code": e.status_code,
                "detail": e.detail,
                "url": e.http_request.url if e.http_request else None,
                "response_content": e.json() if e.content else None,
            }
        )
        # Re-raise or handle as needed
        raise
```

## Best Practices

### Create Meaningful Exception Classes

```python
class UserNotFoundError(lima_api.LimaException):
    detail = "User not found"

class UserAlreadyExistsError(lima_api.LimaException):
    detail = "User already exists"

class InsufficientPermissionsError(lima_api.LimaException):
    detail = "Insufficient permissions to perform this action"
```

### Use Response Models for Structured Error Handling

```python
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict = {}

class ApiError(lima_api.LimaException):
    model = ErrorResponse
```

### Read errors ussing `response` function

```python
async def safe_api_call():
    try:
        return await client.some_method()
    except ApiError as e:
        error = e.response(default=None)
        if isinstanceof(error, ErrorResponse):
            ...
        elif error is None:
            print("Empty body")
        else:
            print(f"Unexpected error {error}")
        raise
```


### Implement Retry Logic with Exception Handling

```python
@lima_api.get(
    "/retry-data",
    response_mapping={
        403: CustomPermissionError,
        429: CustomRateLimitError,
    }
    retry_mapping={429: lima_api.retry_processors.RetryAfterProcessor},
)
async def get_retry_data(self) -> dict:
    pass
```

### 5. Testing Exception Scenarios

For testing we recoment mock the client funtion directly result, not the http response body.
