# Copyright (c) 2026 Project CHIP Authors
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

# ---- builder ----------------------------------------------------------------
FROM ubuntu:22.04 AS builder

# Build prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config git ca-certificates \
        libnl-3-dev libnl-genl-3-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upstream sources
WORKDIR /src
RUN git init hostap \
    && cd hostap \
    && git remote add origin https://git.w1.fi/hostap.git \
    && git fetch --depth 1 origin ca266cc24d8705eb1a2a0857ad326e48b1408b20 \
    && git checkout FETCH_HEAD

# Copy build configuration, patch, and build
COPY config/hostapd.config /src/hostap/hostapd/.config
COPY config/wpa_supplicant.config /src/hostap/wpa_supplicant/.config
COPY patches/*.patch /src/hostap/patches/

RUN cd hostap \
    && for p in patches/*.patch; do patch -p1 <"$p" || exit 1; done \
    && make -j"$(nproc)" install CONFIG_NO_GITVER=y BINDIR=/usr/local/sbin

# ---- runtime ----------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libnl-3-200 libnl-genl-3-200 libssl3 \
        iw iproute2 wireless-regdb \
    && rm -rf /var/lib/apt/lists/*

# Copy binaries
COPY --from=builder \
    /usr/local/sbin/hostapd \
    /usr/local/sbin/hostapd_cli \
    /usr/local/sbin/wpa_supplicant \
    /usr/local/sbin/wpa_cli \
    /usr/local/sbin/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
