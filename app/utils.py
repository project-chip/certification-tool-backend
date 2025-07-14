#
# Copyright (c) 2023 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import copy
import json
import os
from configparser import ConfigParser
from typing import Any

import click
from click.exceptions import Exit
from config import ATTRIBUTE_MAPPING, VALID_PAIRING_MODES


def __print_json(object: Any) -> None:
    click.echo(__json_string(object))


def __json_string(object: Any) -> str:
    if object is None:
        return "None"
    if isinstance(object, list):
        return json.dumps([item.dict() for item in object], indent=4, default=str)
    else:
        return json.dumps(object.dict(), indent=4, default=str)


def build_test_selection(test_collections, tests_list) -> dict:
    """Build the test selection JSON structure from test_collections and tests_list.

    Args:
        test_collections: Object containing test collections data
        tests_list: List of test IDs to select

    Returns:
        dict: Dictionary containing selected tests organized by collection and suite

    Example:
        tests_list = ["TC-ACE-1.1", "TC_ACE_1_3"]
        test_collections = {
            "SDK YAML Tests": {
                "FirstChipToolSuite": {
                    "TC-ACE-1.1": 1
                },
                "SDK Python Tests": {
                    "Python Testing Suite": {
                    "TC_ACE_1_3": 1
                    }
                }
            }
        }
    """
    selected_tests = {}

    # Convert test IDs to a set for faster lookup and normalize them
    tests_set = {test_id.strip().replace("-", "_").replace(".", "_") for test_id in tests_list}

    # Iterate through test collections
    for collection_name, collection in test_collections.test_collections.items():
        selected_tests[collection_name] = {}

        # Iterate through test suites
        for suite_name, suite in collection.test_suites.items():
            selected_tests[collection_name][suite_name] = {}

            # Iterate through test cases
            for test_case_id, test_case in suite.test_cases.items():
                # Normalize the test case ID for comparison
                normalized_test_case_id = test_case_id.replace("-", "_").replace(".", "_")
                if normalized_test_case_id in tests_set:
                    selected_tests[collection_name][suite_name][test_case_id] = 1

    # Remove empty collections and suites
    selected_tests = {
        collection: {suite: tests for suite, tests in suites.items() if tests}
        for collection, suites in selected_tests.items()
        if any(suites.values())
    }

    return selected_tests


def read_properties_file(file_path: str) -> dict:
    """Read a properties file with sections and return its contents as a dictionary.

    Args:
        file_path (str): Path to the properties file

    Returns:
        dict: Dictionary containing the parsed properties

    Raises:
        FileNotFoundError: If the properties file is not found
        ValueError: If there are invalid values in the properties file
        Exception: For other unexpected errors
    """
    properties = {}

    try:
        config = ConfigParser()
        config.read(file_path)

        for section in config.sections():
            properties[section] = {}
            for key, value in config[section].items():
                if key == "pairing_mode":
                    if value not in VALID_PAIRING_MODES:
                        raise ValueError(
                            f"Invalid pairing_mode value: {value}. "
                            f"Valid values are: {', '.join(VALID_PAIRING_MODES)}"
                        )

                if key in ATTRIBUTE_MAPPING:
                    add_mapped_property(properties, key, value, ATTRIBUTE_MAPPING[key])
                else:
                    add_unmapped_property(properties, key, value, section)

        return properties
    except FileNotFoundError:
        click.echo(f"Properties file not found: {file_path}", err=True)
        raise Exit(code=1)
    except ValueError as e:
        click.echo(f"Error in properties file: {str(e)}", err=True)
        raise Exit(code=1)
    except Exception as e:
        click.echo(f"Error reading properties file: {str(e)}", err=True)
        raise Exit(code=1)


def add_mapped_property(properties: dict, key: str, value: str, section_path: tuple) -> None:
    """Add a mapped property to the properties dictionary.

    Args:
        properties (dict): The properties dictionary to update
        key (str): The property key
        value (str): The property value
        section_path (tuple): The path to the section where the property should be added
    """
    current = properties

    # Create nested structure
    for section in section_path[:-1]:
        if section not in current:
            current[section] = {}
        current = current[section]

    # Add the value to the final section
    if section_path[-1] not in current:
        current[section_path[-1]] = {}
    current[section_path[-1]][key] = value


def add_unmapped_property(properties: dict, key: str, value: str, current_section: str) -> None:
    """Add an unmapped property to the properties dictionary.

    Args:
        properties (dict): The properties dictionary to update
        key (str): The property key
        value (str): The property value
        current_section (str): The current section name
    """
    if current_section:
        properties[current_section][key] = value
    else:
        properties[key] = value


def merge_properties_to_config(config_data: dict, default_config: dict) -> dict:
    """Map properties values to the default_config structure.

    Args:
        config_data: Dictionary with properties values organized by main sections
        default_config: Dictionary with default configuration values

    Returns:
        Updated configuration dictionary with properties values mapped to the correct structure
    """
    config_dict = copy.deepcopy(default_config)
    # Convert default_config to dict if it's not already
    config_dict = config_dict.__dict__ if hasattr(config_dict, "__dict__") else config_dict

    # Process network section if it exists
    if "network" in config_data:
        # Create new network section
        new_network = {}

        # Process thread section
        if "thread" in config_data["network"]:
            new_network["thread"] = config_data["network"]["thread"]

        # Process wifi section
        if "wifi" in config_data["network"]:
            new_network["wifi"] = config_data["network"]["wifi"]
        else:
            new_network["wifi"] = config_dict["network"]["wifi"]

        # Replace the entire network section
        config_dict["network"] = new_network

    # Process dut_config section
    if "dut_config" in config_data:
        dut_data = config_data["dut_config"]
        if "pairing_mode" in dut_data:
            config_dict["dut_config"]["pairing_mode"] = dut_data["pairing_mode"]
        if "setup_code" in dut_data:
            config_dict["dut_config"]["setup_code"] = dut_data["setup_code"]
        if "discriminator" in dut_data:
            config_dict["dut_config"]["discriminator"] = dut_data["discriminator"]
        if "chip_use_paa_certs" in dut_data:
            config_dict["dut_config"]["chip_use_paa_certs"] = dut_data["chip_use_paa_certs"].lower() == "true"
        if "trace_log" in dut_data:
            config_dict["dut_config"]["trace_log"] = dut_data["trace_log"].lower() == "true"

    # Process test_parameters section
    if "test_parameters" in config_data:
        config_dict["test_parameters"] = config_data["test_parameters"]

    return config_dict


def convert_nested_to_dict(obj, _seen=None):
    """Convert an object and all its nested objects to dictionaries, handling circular references."""
    if _seen is None:
        _seen = set()

    # Handle None and primitive types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle thread objects and other special types
    if isinstance(obj, (type, object)) and not hasattr(obj, "__dict__"):
        return str(obj)

    # Check for circular references
    obj_id = id(obj)
    if obj_id in _seen:
        return str(obj)
    _seen.add(obj_id)

    # Convert object to dict
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            # Skip special attributes and thread-related objects
            if key.startswith("__") or isinstance(value, type):
                continue
            try:
                result[key] = convert_nested_to_dict(value, _seen)
            except (RecursionError, AttributeError):
                result[key] = str(value)
        return result

    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [convert_nested_to_dict(item, _seen) for item in obj]

    # Handle dictionaries
    if isinstance(obj, dict):
        return {k: convert_nested_to_dict(v, _seen) for k, v in obj.items()}

    # Fallback for other types
    return str(obj)


def parse_pics_xml(xml_content: str) -> dict:
    """Parse a PICS XML file and convert it to the required JSON format.

    Args:
        xml_content (str): The XML content as a string

    Returns:
        dict: Dictionary containing the PICS configuration in the required format
    """
    import xml.etree.ElementTree as ET
    from typing import Any, Dict

    def parse_pics_items(element) -> Dict[str, Any]:
        items = {}
        for pics_item in element.findall(".//picsItem"):
            item_number = pics_item.find("itemNumber").text
            support = pics_item.find("support").text.lower() == "true"
            items[item_number] = {"number": item_number, "enabled": support}
        return items

    try:
        root = ET.fromstring(xml_content)
        cluster_name = root.find("name").text

        # Initialize the result structure
        result = {"clusters": {cluster_name: {"name": cluster_name, "items": {}}}}

        # Parse usage items
        usage_items = parse_pics_items(root.find(".//usage"))
        result["clusters"][cluster_name]["items"].update(usage_items)

        # Parse server side items
        server_side = root.find(".//clusterSide[@type='Server']")
        if server_side is not None:
            # Parse attributes
            attr_items = parse_pics_items(server_side.find(".//attributes"))
            result["clusters"][cluster_name]["items"].update(attr_items)

            # Parse events
            event_items = parse_pics_items(server_side.find(".//events"))
            result["clusters"][cluster_name]["items"].update(event_items)

        return result

    except ET.ParseError as e:
        raise ValueError(f"Failed to parse XML: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing PICS XML: {str(e)}")


def read_pics_config(pics_config_folder: str) -> dict:
    """Read PICS configuration from XML files in the specified folder.

    Args:
        pics_config_folder (str): Path to the folder containing PICS XML files

    Returns:
        dict: Dictionary containing the PICS configuration

    Raises:
        Exit: If there are any errors reading or parsing the PICS configuration
    """
    pics = {"clusters": {}}
    if not pics_config_folder:
        return pics

    try:
        # Resolve the path to handle relative paths correctly
        pics_config_folder = os.path.abspath(pics_config_folder)
        if os.path.isdir(pics_config_folder):
            # Read all XML files from the directory
            for filename in os.listdir(pics_config_folder):
                if filename.endswith(".xml"):
                    file_path = os.path.join(pics_config_folder, filename)
                    try:
                        with open(file_path, "r") as f:
                            xml_content = f.read()
                            cluster_pics = parse_pics_xml(xml_content)
                            # Merge the cluster PICS into the global structure
                            pics["clusters"].update(cluster_pics["clusters"])
                    except Exception as e:
                        click.echo(f"Failed to parse PICS XML file {filename}: {e}")
                        raise Exit(code=1)
        else:
            click.echo(f"Error: {pics_config_folder} is not a directory")
            raise Exit(code=1)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        click.echo(f"Failed to read PICS configuration: {e}")
        raise Exit(code=1)

    return pics
