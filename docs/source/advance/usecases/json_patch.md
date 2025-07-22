# Json patch

Here is an example of how to call to [rfc6902](https://datatracker.ietf.org/doc/html/rfc6902) (aka json-patch).

The protocol requires two objects to make the diffing between its and send only the changes. To do that, we use [jsonpatch](https://pypi.org/project/jsonpatch/) lib to make it.


```python
import jsonpatch
import lima_api

class AsyncClient(lima_api.LimaApi):

    def close_by_id(self, item_id: int) -> None:
        payload = [
            {
                "op": "replace",
                "path": "/status",
                "value": "CLOSED"
            }
        ]
        self.patch(item_id=item_id, data=payload)
    
    def apply_changes(self, item_id: int, orig: Any, dest: Any) -> None:
        if isinstanceof(orig, dict):
            orig_dict = orig
        else:
            orig_dict = orig.json()
        if isinstanceof(dest, dict):
            dest_dict = dest
        else:
            dest_dict = dest.json()
        patch_data = jsonpatch.make_patch(orig_dict, dest_dict)
        self.patch(item_id=item_id, data=patch_data)

    @lima_api.patch(
        "/json-patch/{item_id}",
        default_response_code=status.HTTP_204_NO_CONTENT,
        headers={"Content-Type": "application/json-patch+json"}
    )
    def patch(
            self,
            *,
            item_id: int = lima_api.PathParameter(),
            data: List[dict]
    ) -> None:
        ...

```
