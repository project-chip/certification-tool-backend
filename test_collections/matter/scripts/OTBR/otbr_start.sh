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
ROOT_DIR=$(realpath $(dirname "$0")/../../../../..)
TH_SCRIPTS_DIR="$ROOT_DIR/scripts"

BR_INTERFACE="eth0"
BR_VARIANT="35"
BR_CHANNEL=25 # The Thread communication channel used
BR_IMAGE_BASE="nrfconnect/otbr"
BR_IMAGE_TAG="9185bda"
BR_IMAGE=$BR_IMAGE_BASE":"$BR_IMAGE_TAG

while getopts ":i:v:" opt; do
  case $opt in
    i)
      echo "Using BR Interface: $OPTARG" >&2
      BR_INTERFACE=$OPTARG
      ;;
    v)
      echo "Using BR Variant: $OPTARG" >&2
      BR_VARIANT=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Removing 'otbr-chip' container"
docker stop otbr-chip > /dev/null 2>&1
docker rm otbr-chip > /dev/null 2>&1

# Also remove any other leftover container from the OTBR image (e.g. one started by
# the Test Harness itself via otbr_manager.py, which doesn't use the 'otbr-chip' name).
# A stale container like this can still be holding the RCP serial device, which makes
# otbr-agent fail to attach in the container we're about to start (see #1071).
STALE_OTBR_CONTAINERS=$(sudo docker ps -aq --filter "ancestor=$BR_IMAGE")
if [ -n "$STALE_OTBR_CONTAINERS" ]; then
	echo "$STALE_OTBR_CONTAINERS" | xargs -r sudo docker stop > /dev/null 2>&1
	echo "$STALE_OTBR_CONTAINERS" | xargs -r sudo docker rm -f > /dev/null 2>&1
fi

if docker images | grep $BR_IMAGE_BASE | grep $BR_IMAGE_TAG;
then
	echo "otbr image "$BR_IMAGE" already installed"
else
	print_script_step "Pulling $BR_IMAGE image"
	docker pull $BR_IMAGE || exit 1
fi

print_script_step "Checking Thread RCP device"
RCP_DEVICE="/dev/ttyACM0"
if [ ! -e "$RCP_DEVICE" ]; then
	echo "ERROR: $RCP_DEVICE not found. Is the Thread RCP dongle plugged in?" >&2
	echo "If it was just plugged in/out, wait a few seconds for it to enumerate and try again." >&2
	exit 1
fi

print_script_step "Starting 'otbr-chip' container"
AVAHI_PATH=$ROOT_DIR/backend/app/otbr_manager/avahi
sudo modprobe ip6table_filter || exit 1
sudo docker run --privileged -d --network host --name otbr-chip -e NAT64=1 -e DNS64=0 -e WEB_GUI=0 -v $AVAHI_PATH:/etc/avahi -v $RCP_DEVICE:/dev/radio $BR_IMAGE --radio-url spinel+hdlc+uart:///dev/radio?uart-baudrate=115200 -B $BR_INTERFACE || exit 1

print_script_step "Waiting for the OTBR agent to become ready..."
OTBR_READY_TIMEOUT=30
OTBR_READY=0
for ((i = 0; i < OTBR_READY_TIMEOUT; i++)); do
	if sudo docker exec otbr-chip ot-ctl state > /dev/null 2>&1; then
		OTBR_READY=1
		break
	fi
	sleep 1
done

if [ $OTBR_READY -eq 0 ]; then
	echo "ERROR: otbr-agent did not become ready within ${OTBR_READY_TIMEOUT}s." >&2
	echo "Dumping 'otbr-chip' container logs for diagnosis:" >&2
	sudo docker logs otbr-chip
	exit 1
fi

BR_PANID="5b${BR_VARIANT}" # The 2-byte Personal Area Network ID is a unique Thread identifier
BR_EXTPANID="5b${BR_VARIANT}dead5b${BR_VARIANT}beef" # The 8-byte Extended Personal Area Network ID is a unique Thread identifier
BR_NETWORKNAME="5b${BR_VARIANT}" # The human-readable Network Name is a unique Thread identifier
BR_IPV6PREFIX="fd11:${BR_VARIANT}::/64" # The Mesh-Local prefix used to reach interfaces in the same network
BR_NETWORKKEY="00112233445566778899aabbccddeeff" # The Thread authentication key value

BR_PARAMS=(
"dataset init new"
"dataset channel ${BR_CHANNEL}"
"dataset panid 0x${BR_PANID}"
"dataset extpanid ${BR_EXTPANID}"
"dataset networkname ${BR_NETWORKNAME}"
"dataset networkkey ${BR_NETWORKKEY}"
"dataset commit active"
"prefix add ${BR_IPV6PREFIX} pasor"
"ifconfig up"
"thread start"
"netdata register"
)

print_script_step "Setting up Thread Network"

for i in "${BR_PARAMS[@]}"
do
  if [[ "$i" == dataset\ networkkey* ]]; then
    printf "Param: 'dataset networkkey [REDACTED]'"
  else
    printf "Param: '$i'"
  fi
        if ! sudo docker exec -t otbr-chip ot-ctl $i; then
                echo "ERROR: 'ot-ctl $i' failed. Dumping 'otbr-chip' container logs for diagnosis:" >&2
                sudo docker logs otbr-chip
                exit 1
        fi
done

if ! ACTIVE_DATASET_OUTPUT=$(sudo docker exec otbr-chip ot-ctl dataset active -x); then
  echo "ERROR: Failed to read the OTBR Active Dataset." >&2
  exit 1
fi

ACTIVE_DATASET=$(printf '%s\n' "$ACTIVE_DATASET_OUTPUT" | tr -d '\r' | awk '/^[0-9a-fA-F]+$/ { print; exit }')
if [[ -z "$ACTIVE_DATASET" ]]; then
  echo "ERROR: OTBR returned an invalid Active Dataset." >&2
  exit 1
fi

ACTIVE_DATASET_PATH="/tmp/otbr_simple_dataset.txt"
printf '%s\n' "$ACTIVE_DATASET" | sudo tee "$ACTIVE_DATASET_PATH" > /dev/null
sudo chmod 600 "$ACTIVE_DATASET_PATH"
ACTIVE_DATASET_FINGERPRINT=$(printf '%s' "$ACTIVE_DATASET" | xxd -r -p | sha256sum | awk '{ print $1 }')
printf "Active Dataset SHA-256: %s\n" "$ACTIVE_DATASET_FINGERPRINT"

print_script_step "Restarting the Raspi avahi to have it in a clean state"
sudo service avahi-daemon restart

print_end_of_script

