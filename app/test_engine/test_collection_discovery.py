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
import importlib
import traceback
from inspect import getmembers, isclass
from os import scandir
from pathlib import Path
from pkgutil import walk_packages
from typing import Dict, List, Optional, Type, TypeVar

from loguru import logger

from app.test_engine.models import TestCase, TestSuite

from .models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
    TestSuiteDeclaration,
)

T = TypeVar("T")
COLLECTIONS_DIRNAME = "test_collections"
DISABLED_COLLECTIONS_FILENAME = ".disabled_test_collections"
DISABLED_TEST_CASES_FILENAME = ".disabled_test_cases"

ROOT_PATH = Path(__file__).parent.parent.parent
COLLECTIONS_PATH = ROOT_PATH / COLLECTIONS_DIRNAME
DISABLED_COLLECTIONS_FILEPATH = COLLECTIONS_PATH / DISABLED_COLLECTIONS_FILENAME
DISABLED_TEST_CASES_FILEPATH = COLLECTIONS_PATH / DISABLED_TEST_CASES_FILENAME


def disabled_test_collections() -> List[str]:
    """Returns a list of collection names that should be disabled.

    Each line in the file at DISABLED_COLLECTIONS_FILEPATH corresponds to a
    folder/collection name to be disabled.

    File content example:
        tool_unit_tests

    Returns:
        List[str]: list of filtered folder names
    """
    return __extract_lines_from_file(DISABLED_COLLECTIONS_FILEPATH)


def disabled_test_cases() -> List[str]:
    """Returns a list of public ids from test cases that should be disabled.

    Each line in the file at DISABLED_TEST_CASES_FILEPATH corresponds to a test case
    public id to be disabled.

    File content example:
        TC_ACL_2_1

    Returns:
        List[str]: list of filtered test case public ids
    """
    return __extract_lines_from_file(DISABLED_TEST_CASES_FILEPATH)


def __extract_lines_from_file(file_path: Path) -> List[str]:
    """Returns a list of strings extracted from a file.

    Each line in the file corresponds to a item in the list.

    Returns:
        List[str]: list of file lines
    """
    if not file_path.exists():
        logger.warning(f"No file found at #{file_path}")
        return []

    # Load the config from file as a dictionary.
    with open(file_path) as file:
        return file.read().splitlines()


def discover_test_collections(
    disabled_collections: list[str] = disabled_test_collections(),
    disabled_test_cases: list[str] = disabled_test_cases(),
) -> Dict[str, TestCollectionDeclaration]:
    """Dynamically discover test_collection modules in `test_collections` folder.

    Collections will be discovered in two ways:

    - Directly declared TestCollectionDeclaration variables in the module
    initializers. Eg. `yaml_tests`

    - Dynamically generated collection based on scanning a subfolder for TestSuite and
    TestCase classes. Eg. `sample_tests`

    Note that disabled_test_cases and disabled_collections can be used to disable both
    entire collections or individual test cases.
    """
    collections: Dict[str, TestCollectionDeclaration] = {}

    names = __test_collection_folder_names()

    for name in names:
        # Don't add collection if it doesn't have any suites
        if found_collections := __find_test_collections(name, disabled_test_cases):
            for collection in found_collections:
                if collection.name not in disabled_collections:
                    collections[collection.name] = collection

    return collections


def __find_classes_of_type(module_name: str, classtype: Type[T]) -> List[Type[T]]:
    """Dynamically find classes of specified type in the specified module.

    Limitations:
    - Finds classes by importing packages so desired classes have to be discoverable
    that way, i.e. classes are in a package and imported into the __init__.py file.
    """
    module = importlib.import_module(module_name)

    # module.__file__ is of type:
    #   - collections: '<COLLECTIONS_PATH>/<collection>/__init__.py'
    #   - test suites: '<COLLECTIONS_PATH>/<collection>/<suite>/<suite_file>.py'
    # We want to find the classes in the same level as the specified module, so we use
    # the parent as the path in walk_packages
    file_path = module.__file__

    # __file__ is optional because "It might be missing for certain types of modules,
    # such as C modules that are statically linked into the interpreter, and  the import
    # system may opt to leave it unset if it has no semantic meaning" (Python docs)
    if not file_path:
        logger.warning(f"for {module_name} __file__ was unexpectedly None.")
        return []
    package_path = Path(file_path).parent

    # Prefix to add to the module names found in walk_packages
    module_package = module.__package__
    if not module_package:
        return []
    prefix = module_package + "."

    classes = []
    for _, submodule_name, is_package in walk_packages([str(package_path)], prefix):
        if is_package:
            try:
                submodule = importlib.import_module(submodule_name)

            except Exception:
                logger.error(traceback.format_exc())
                continue

            for _, obj in getmembers(submodule):
                if isclass(obj) and issubclass(obj, classtype):
                    classes.append(obj)

    return classes


def __declared_collection_declarations(
    collection_module_name: str,
) -> list[TestCollectionDeclaration]:
    """This will check '<COLLECTIONS_PATH>/<collection>/__init__.py' for declarations of
    one or more TestCollectionDeclarations.
    """
    collections = []
    module = importlib.import_module(collection_module_name)
    for _, obj in getmembers(module):
        if isinstance(obj, TestCollectionDeclaration):
            collections.append(obj)

    return collections


def __find_test_collections(
    folder_name: str,
    disabled_test_cases: Optional[list[str]],
) -> Optional[list[TestCollectionDeclaration]]:
    """Finds test collections based on folder name.

    Either by:
    - finding pre-declared TestCollectionDeclarations declared in a module.
    - dynamically scanning the specified folder for TestSuites (based on class)
      including their TestCases.

    Limitations:
    - Finds suites / test cases by importing packages so desired classes have to be
    discoverable that way, i.e. classes are in a package.
    - TestSuites cannot be nested, i.e. one  root TestSuite for a set of test cases.
    - TestCases are nested within a TestSuite.
    """
    collection_module_name = f"{COLLECTIONS_DIRNAME}.{folder_name}"

    test_collections = __declared_collection_declarations(collection_module_name)

    # Remove disabled test cases from collections
    if disabled_test_cases:
        __remove_disabled_test_cases(test_collections, disabled_test_cases)

    return test_collections


def __remove_disabled_test_cases(
    test_collections: list[TestCollectionDeclaration],
    disabled_test_cases: list[str],
) -> None:
    """Remove the disabled test cases from a list of test collections.

    If all test cases from a test suite are disabled, the test suite is removed from the
    test collection. If all test suites from a test collection are removed, then the
    collection itself is also removed form the list.

    Args:
        test_collections (list[TestCollectionDeclaration]): The test collections list.
        disabled_test_cases (list[str]): The list of the disabled test cases.
    """
    emptied_collections = []

    for index, collection in enumerate(test_collections):
        emptied_suites = []

        for key, suite_decl in collection.test_suites.items():
            suite_decl.test_cases = {
                k: v
                for k, v in suite_decl.test_cases.items()
                if v.public_id not in disabled_test_cases
            }
            if not suite_decl.test_cases:
                emptied_suites.append(key)

        for emptied_suite in emptied_suites:
            del collection.test_suites[emptied_suite]

        if not collection.test_suites:
            emptied_collections.append(index)

    for emptied_collection in emptied_collections:
        del test_collections[emptied_collection]


def __find_test_suite(
    suite: Type[TestSuite],
) -> Optional[TestSuiteDeclaration]:
    """Dynamically finds TestCases in the specified suite.

    Limitations:
    - Finds test cases by importing packages so desired classes have to be discoverable
    that way, i.e. classes are in a package.
    - TestCases are nested within a TestSuite.
    """
    test_cases: List[Type[TestCase]] = __find_classes_of_type(
        module_name=suite.__module__, classtype=TestCase
    )

    # Don't include empty test suites
    if not test_cases:
        return None

    mandatory = False
    if "mandatory" in suite.metadata:
        mandatory = suite.metadata["mandatory"]  # type: ignore

    suite_declaration = TestSuiteDeclaration(suite, mandatory=mandatory)
    for test in test_cases:
        test_declaration = TestCaseDeclaration(test)
        suite_declaration.test_cases[test.public_id()] = test_declaration

    return suite_declaration


def test_collection_declaration(
    collection_path: Path, name: str, mandatory: bool = False
) -> Optional[TestCollectionDeclaration]:
    """Declare a new collection of test suites."""
    collection = TestCollectionDeclaration(str(collection_path), name, mandatory)

    collection_module_name = __collection_module_name(collection_path)
    suite_types = __find_classes_of_type(
        module_name=collection_module_name, classtype=TestSuite
    )

    for suite_type in suite_types:
        if suite := __find_test_suite(suite_type):
            collection.add_test_suite(suite)

    return collection if collection.test_suites else None


def __collection_module_name(path: Path) -> str:
    """Get the name of the module that should be searched for the collection's test
    suites.

    The module name is extracted from the collection folder path. This function iterates
    over the parts of the path until it finds COLLECTIONS_DIRNAME. Then it creates the
    module name string with the remaining parts.

    Args:
        path (Path): Collection folder path.

    Returns:
        str: Collection module name starting w
    """
    found_collections_directory = False
    collection_module_name = COLLECTIONS_DIRNAME

    for part in path.parts:
        if found_collections_directory:
            collection_module_name += f".{part}"
        elif part == COLLECTIONS_DIRNAME:
            found_collections_directory = True

    return collection_module_name


def __test_collection_folder_names() -> List[str]:
    """This will return all folder names for sub-folder in the test collections
    folder.

    Returns:
        List[str]: list of all folder names
    """
    return [f.name for f in scandir(COLLECTIONS_PATH) if f.is_dir()]
