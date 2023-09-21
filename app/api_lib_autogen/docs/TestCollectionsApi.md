<!--
 *
 * Copyright (c) 2023 Project CHIP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
-->
# api_lib_autogen.TestCollectionsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**read_test_collections_api_v1_test_collections_get**](TestCollectionsApi.md#read_test_collections_api_v1_test_collections_get) | **GET** /api/v1/test_collections/ | Read Test Collections


# **read_test_collections_api_v1_test_collections_get**
> TestCollections read_test_collections_api_v1_test_collections_get()

Read Test Collections

Retrieve available test collections.

### Example

```python
from __future__ import print_function
import time
import api_lib_autogen
from api_lib_autogen.rest import ApiException
from pprint import pprint

# Create an instance of the API class
api_instance = api_lib_autogen.TestCollectionsApi()

try:
    # Read Test Collections
    api_response = api_instance.read_test_collections_api_v1_test_collections_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling TestCollectionsApi->read_test_collections_api_v1_test_collections_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**TestCollections**](TestCollections.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

