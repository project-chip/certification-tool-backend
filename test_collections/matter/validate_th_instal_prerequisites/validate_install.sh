#! /usr/bin/env bash

 #
 # Copyright (c) 2024 Project CHIP Authors
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
set -e


# Usage: ./test_collections/matter/scripts/update-paa-certs.sh

apt-get update -y

# Paths
MATTER_PACKAGE_LIST_FILE="/app/certification-tool/backend/test_collections/matter/scripts/package-dependency-list.txt"
TH_PACKAGE_LIST_FILE="/app/certification-tool/scripts/ubuntu/package-dependency-list.txt"

readarray matter_package_list < "$MATTER_PACKAGE_LIST_FILE"

readarray th_package_list < "$MATTER_PACKAGE_LIST_FILE"

SAVEIFS=$IFS
for package in ${th_package_list[@]}; do
  echo "Instaling package: ${package[@]}"
  DEBIAN_FRONTEND=noninteractive apt-get satisfy ${package[@]} -y --allow-downgrades  1> /dev/null
done

for package in ${matter_package_list[@]}; do
  echo "Instaling package: ${package[@]}"
  DEBIAN_FRONTEND=noninteractive apt-get satisfy ${package[@]} -y --allow-downgrades 1> /dev/null
done


