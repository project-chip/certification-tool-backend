#! /usr/bin/env bash

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
set -e
MATTER_PROGRAM_DIR=$(realpath $(dirname "$0")/..)
TH_SCRIPTS_DIR="$MATTER_PROGRAM_DIR/../../../scripts"

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Pulling chip-cert-bins docker image"

# We are fetching SDK docker image and tag name from backend
# This is done to minimize the places the SDK version is tracked.
SDK_DOCKER_PACKAGE=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_IMAGE | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_TAG=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_TAG | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_IMAGE=$SDK_DOCKER_PACKAGE:$SDK_DOCKER_TAG

HOST_ARCH=$(uname -m)

# Map host architecture to Docker platform architecture
case "$HOST_ARCH" in
    x86_64)  DOCKER_ARCH="amd64" ;;
    aarch64) DOCKER_ARCH="arm64" ;;
    armv7l)  DOCKER_ARCH="arm"   ;;
    *)       DOCKER_ARCH="$HOST_ARCH" ;;
esac

DOCKER_IMAGE_FOUND=$(sudo docker images -q $SDK_DOCKER_IMAGE)

if [[ -z "$DOCKER_IMAGE_FOUND" ]]; then
    print_script_step "Pulling '$SDK_DOCKER_IMAGE' image"

    # Check if the image manifest has our architecture before pulling
    PULL_FAILED=0
    sudo docker pull $SDK_DOCKER_IMAGE 2>/dev/null || PULL_FAILED=1

    if [[ $PULL_FAILED -eq 1 ]]; then
        echo ""
        echo "********************************************************************************"
        echo "WARNING: The pre-built SDK image '$SDK_DOCKER_IMAGE'"
        echo "         does not have a build for your architecture ($HOST_ARCH / $DOCKER_ARCH)."
        echo ""
        echo "The pre-built image is currently only available for arm64 (Raspberry Pi)."
        echo ""
        echo "You have the following options:"
        echo ""
        echo "  1) Build the image locally (this will compile the Matter SDK from source"
        echo "     for your platform and may take 2-3+ hours)"
        echo ""
        echo "  2) Skip sample apps for now, you can manually build individual apps for your"
        echo "     architecture later from the Matter SDK source, then copy the binaries to"
        echo "     ~/apps/"
        echo ""
        echo "  3) Abort installation"
        echo "********************************************************************************"
        echo ""

        select choice in "Build locally" "Skip sample apps" "Abort"; do
            case $choice in
                "Build locally")
                    print_script_step "Building SDK image locally for $DOCKER_ARCH (this will take a while...)"

                    # Determine architecture-specific target prefix
                    case "$DOCKER_ARCH" in
                        amd64) ARCH_PREFIX="linux-x64" ;;
                        arm64) ARCH_PREFIX="linux-arm64" ;;
                        *)     ARCH_PREFIX="linux-x64" ;;
                    esac

                    BUILD_DIR=$(mktemp -d)

                    # Generate a minimal Dockerfile that builds only essential apps.
                    # This avoids the full upstream Dockerfile which builds 30+ apps
                    # and requires 16GB+ RAM for parallel compilation.
                    cat > "$BUILD_DIR/Dockerfile" << DOCKERFILE_EOF
FROM ubuntu:22.04 AS chip-build-cert
ARG COMMITHASH=main
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \\
    git gcc g++ pkg-config libssl-dev libdbus-1-dev \\
    libglib2.0-dev libavahi-client-dev ninja-build python3-venv \\
    python3-dev python3-pip unzip libgirepository1.0-dev \\
    libcairo2-dev libreadline-dev generate-ninja curl wget \\
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /root/connectedhomeip
RUN git clone https://github.com/project-chip/connectedhomeip.git /root/connectedhomeip
WORKDIR /root/connectedhomeip/
RUN git checkout \${COMMITHASH}
RUN ./scripts/checkout_submodules.py --allow-changing-global-git-config --shallow --platform linux
RUN bash scripts/bootstrap.sh

FROM chip-build-cert AS chip-build-cert-bins
SHELL ["/bin/bash", "-c"]

RUN git rev-parse HEAD > /root/.sdk-sha-version

# Build only essential apps with limited parallelism (-j4)
RUN set -x \\
    && source scripts/activate.sh \\
    && scripts/build/build_examples.py \\
    --target ${ARCH_PREFIX}-chip-tool-ipv6only-platform-mdns-nfc-commission \\
    --target ${ARCH_PREFIX}-shell-ipv6only-platform-mdns \\
    --target ${ARCH_PREFIX}-chip-cert-ipv6only-platform-mdns \\
    --target ${ARCH_PREFIX}-air-purifier-ipv6only \\
    --target ${ARCH_PREFIX}-all-clusters-ipv6only \\
    --target ${ARCH_PREFIX}-all-clusters-ipv6only-nlfaultinject \\
    --target ${ARCH_PREFIX}-all-clusters-minimal-ipv6only \\
    build -- -j4 \\
    && mv out/${ARCH_PREFIX}-chip-tool-ipv6only-platform-mdns-nfc-commission/chip-tool out/chip-tool \\
    && mv out/${ARCH_PREFIX}-shell-ipv6only-platform-mdns/chip-shell out/chip-shell \\
    && mv out/${ARCH_PREFIX}-chip-cert-ipv6only-platform-mdns/chip-cert out/chip-cert \\
    && mv out/${ARCH_PREFIX}-air-purifier-ipv6only/chip-air-purifier-app out/chip-air-purifier-app \\
    && mv out/${ARCH_PREFIX}-all-clusters-ipv6only/chip-all-clusters-app out/chip-all-clusters-app \\
    && mv out/${ARCH_PREFIX}-all-clusters-ipv6only-nlfaultinject/chip-all-clusters-app out/chip-all-clusters-app-nlfaultinject \\
    && mv out/${ARCH_PREFIX}-all-clusters-minimal-ipv6only/chip-all-clusters-minimal-app out/chip-all-clusters-minimal-app

FROM ubuntu:22.04
RUN mkdir /root/connectedhomeip
WORKDIR /root/connectedhomeip/
RUN mkdir -p apps out credentials mock_server
COPY --from=chip-build-cert-bins /root/.sdk-sha-version /root/.sdk-sha-version
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-tool apps/chip-tool
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-shell apps/chip-shell
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-cert apps/chip-cert
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-air-purifier-app apps/chip-air-purifier-app
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-all-clusters-app apps/chip-all-clusters-app
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-all-clusters-app-nlfaultinject apps/chip-all-clusters-app-nlfaultinject
COPY --from=chip-build-cert-bins /root/connectedhomeip/out/chip-all-clusters-minimal-app apps/chip-all-clusters-minimal-app
COPY --from=chip-build-cert-bins /root/connectedhomeip/credentials credentials
DOCKERFILE_EOF

                    echo ""
                    echo "Building essential apps only (7 of 30+) with limited parallelism (-j4)."
                    echo "This avoids running out of memory on systems with less than 16GB RAM."
                    echo ""
                    echo "Building image (this may take 1-2 hours)..."
                    sudo docker buildx build \
                        --load \
                        --build-arg COMMITHASH="$SDK_DOCKER_TAG" \
                        --tag "$SDK_DOCKER_IMAGE" \
                        "$BUILD_DIR"

                    rm -rf "$BUILD_DIR"
                    echo ""
                    echo "Local build complete!"
                    echo ""
                    echo "NOTE: Only essential apps were built. To build additional apps later:"
                    echo "  1. Start the image:  docker run -it $SDK_DOCKER_IMAGE bash"
                    echo "  2. Build more apps:  source scripts/activate.sh && scripts/build/build_examples.py --target <target-name> build"
                    echo "  3. Copy binaries out: docker cp <container>:/root/connectedhomeip/out/<target>/app ~/apps/"
                    echo ""
                    break
                    ;;
                "Skip sample apps")
                    print_script_step "Skipping sample apps setup"
                    echo "Sample apps were not installed."
                    echo "You can build individual apps later from the Matter SDK source."
                    print_end_of_script
                    exit 0
                    ;;
                "Abort")
                    echo "Installation aborted by user."
                    exit 1
                    ;;
                *)
                    echo "Invalid option. Please select 1, 2, or 3."
                    ;;
            esac
        done
    fi
else
    echo "SDK Docker image already exists"
    echo "$SDK_DOCKER_IMAGE"
fi


print_script_step "Updating Sample APPs"
sudo docker run -t -v ~/apps:/apps -v ~/mock_server:/mock_server -v ~/credentials:/credentials $SDK_DOCKER_IMAGE bash -c "rm -v /apps/*; rm -vrf /mock_server/*; rm -vrf /credentials/*; cp -v apps/* /apps/; cp -v -r mock_server/* /mock_server/; cp -v -r credentials/* /credentials/"
echo "Setting Sample APPs ownership"
sudo chown -R `whoami` ~/apps

print_end_of_script
