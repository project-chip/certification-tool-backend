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
MATTER_PROGRAM_DIR=$(dirname "$0")
TH_SCRIPTS_DIR="$MATTER_PROGRAM_DIR/../../../scripts"

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Installing Matter Dependencies"
# TODO Comment on what dependency is required for:
UBUNTU_VERSION_NUMBER=$(lsb_release -sr)
if [[ $UBUNTU_VERSION_NUMBER = 22.04 ]]; then
  packagelist=(
     "apt-transport-https (>=2.4.11)"
     "avahi-utils (>=0.8-5ubuntu5.2)"                 # Matter uses Avahi
     "ca-certificates (=20230311ubuntu0.22.04.1)"
     "figlet (=2.2.5-3)"
     "g++ (=4:11.2.0-1ubuntu1)"
     "gcc (=4:11.2.0-1ubuntu1)"
     "generate-ninja (=0.0~git20220118.0725d78-1)"
     "libavahi-client-dev (=0.8-5ubuntu5.2)"
     "libcairo2-dev (=1.16.0-5ubuntu2)"
     "libdbus-1-dev (=1.12.20-2ubuntu4.1)"
     "libgirepository1.0-dev (=1.72.0-1)"
     "libglib2.0-dev (>=2.72.4-0ubuntu2.2)"
     "libreadline-dev (=8.1.2-1)"
     "libssl-dev (>=3.0.2-0ubuntu1.14)"               # Apparently with each update, previous versions of the library are removed
     "net-tools (=1.60+git20181103.0eebece-1ubuntu5)"
     "ninja-build (=1.10.1-1)"
     "npm (=8.5.1~ds-1)"
     "pkg-config (=0.29.2-1ubuntu3)"
     "software-properties-common (=0.99.22.9)"
     "toilet (=0.3-1.4)"
     "unzip (>=6.0-26ubuntu3.1)"
  )
elif [[ $UBUNTU_VERSION_NUMBER = 24.04 ]]; then
  packagelist=(
     "apt-transport-https (>=2.7.14build2)"
     "avahi-utils (>=0.8-13ubuntu6)"                 # Matter uses Avahi
     "ca-certificates (=20240203)"
     "figlet (=2.2.5-3)"
     "g++ (=4:13.2.0-7ubuntu1)"
     "gcc (=4:13.2.0-7ubuntu1)"
     "generate-ninja (=0.0~git20240221.03d10f1-1)"
     "libavahi-client-dev (=0.8-13ubuntu6)"
     "libcairo2-dev (=1.18.0-3build1)"
     "libdbus-1-dev (=1.14.10-4ubuntu4)"
     "libgirepository1.0-dev (=1.80.1-1)"
     "libglib2.0-dev (>=2.80.0-6ubuntu3.1)"
     "libreadline-dev (=8.2-4build1)"
     "libssl-dev (>=3.0.13-0ubuntu3.1)"               # Apparently with each update, previous versions of the library are removed
     "net-tools (=2.10-0.1ubuntu4)"
     "ninja-build (=1.11.1-2)"
     "npm (=9.2.0~ds1-2)"
     "pkg-config (=1.8.1-2build1)"
     "software-properties-common (=0.99.48)"
     "toilet (=0.3-1.4build1)"
     "unzip (>=6.0-28ubuntu4)"
  )
else
  printf "###############################################################\n"
  printf "###############################################################\n"
  printf "########## This version of Ubuntu is not supported. ###########\n"
  printf "###############################################################\n"
  printf "###############################################################\n"
  exit 1
fi


SAVEIFS=$IFS
IFS=$(echo -en "\r")
for package in ${packagelist[@]}; do
  print_script_step "Instaling package: ${package[@]}"
  sudo DEBIAN_FRONTEND=noninteractive sudo apt-get satisfy ${package[@]} -y --allow-downgrades 
done
IFS=$SAVEIFS 

print_script_step "Fetching sample apps"
$MATTER_PROGRAM_DIR/scripts/update-sample-apps.sh

print_script_step "Fetching PAA Certs from SDK"
$MATTER_PROGRAM_DIR/scripts/update-paa-certs.sh

print_end_of_script
