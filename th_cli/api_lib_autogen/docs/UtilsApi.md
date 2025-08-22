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
# api_lib_autogen.UtilsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**test_email_api_v1_utils_test_email_post**](UtilsApi.md#test_email_api_v1_utils_test_email_post) | **POST** /api/v1/utils/test-email/ | Test Email


# **test_email_api_v1_utils_test_email_post**
> Msg test_email_api_v1_utils_test_email_post(email_to)

Test Email

Test emails.

### Example

```python
from __future__ import print_function
import time
import api_lib_autogen
from api_lib_autogen.rest import ApiException
from pprint import pprint

# Create an instance of the API class
api_instance = api_lib_autogen.UtilsApi()
email_to = 'email_to_example' # str | 

try:
    # Test Email
    api_response = api_instance.test_email_api_v1_utils_test_email_post(email_to)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling UtilsApi->test_email_api_v1_utils_test_email_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **email_to** | [**str**](.md)|  | 

### Return type

[**Msg**](Msg.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

