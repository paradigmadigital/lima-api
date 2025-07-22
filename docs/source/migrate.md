# Migration Guide

If you're migrating from a previous version or another HTTP library, here are some common patterns:

## From requests library
```python
import requests

try:
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    data = response.json()
except requests.HTTPError as e:
    print(f"HTTP Error: {e.response.status_code}")
```

## From httpx library

```python
import httpx

try:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        data = response.json()
except httpx.HTTPStatusError as e:
    print(f"HTTP Error: {e.response.status_code}")
``` 

## To Lima-API

```python
# New way with Lima-API
import lima_api

class AsyncClient(lima_api.LimaApi):
    @lima_api.get("/data")
    async def get_data(self) -> dict: ...

with AsyncClient() as client:
    try:
        data = await client.get_data()
    except lima_api.LimaException as e:
        print(f"HTTP Error: {e.status_code}")
```
