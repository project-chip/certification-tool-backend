#!/bin/bash

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

# Supervisor for the Wi-Fi Fixture container. Publishes the radios this fixture
# owns, then keeps hostapd and wpa_supplicant running, each with its own subtree
# of the shared directory, which is wiped on startup and if the daemon restarts.
# Neither daemon holds an interface until told to. The fixture itself accepts no
# commands: the daemons' control sockets are the only way to drive the fixture.

set -euo pipefail

# Not configurable: the same path is compiled into the binaries as
# CONFIG_CTRL_IFACE_DIR (see config/), so the two would have to agree.
ROOT=/run/wifi-fixture

log() { printf '%s wifi-fixture: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "$*"; exit 1; }

# Resolves the phy backing an interface, e.g. wlan1 -> phy1. Tests need this for
# `ADD bss_config=<phy>:<conf>`, and only this container can see /sys. Note that
# this reports failure rather than calling die, because it runs inside a command
# substitution where an exit would only leave the subshell.
phy_of() {
    local ifname="$1"
    [[ -d /sys/class/net/$ifname ]] ||
        { log "no interface named '$ifname'"; return 1; }
    [[ -e /sys/class/net/$ifname/phy80211 ]] ||
        { log "'$ifname' is not a wireless interface"; return 1; }
    basename "$(readlink -f "/sys/class/net/$ifname/phy80211")"
}

# Publishes what the fixture actually claimed, rather than what was configured,
# so that a dongle which failed to enumerate stops the container here instead of
# surfacing later as a confusing test failure. One "<ifname> <phy>" per line: the
# record has no structure worth a parser, and neither field can contain a space.
publish_interfaces() {
    local ifnames=() lines=() ifname phy
    IFS=, read -ra ifnames <<<"${WIFI_FIXTURE_IFNAMES:-}"
    [[ -n ${ifnames[0]:-} ]] ||
        die "WIFI_FIXTURE_IFNAMES is not set; it names the radios this fixture owns"

    for ifname in "${ifnames[@]}"; do
        phy="$(phy_of "$ifname")" || exit 1
        lines+=("$ifname $phy")
        log "claimed $ifname ($phy)"
    done

    printf '%s\n' "${lines[@]}" >"$ROOT/interfaces"
}

# Runs one daemon forever, wiping and recreating its subtree each time it starts.
# That makes this the only implementation of "reset the fixture", so a test tears
# down by sending TERMINATE and waiting for the control socket to come back.
supervise() {
    local name="$1" dir="$ROOT/$1" child="" started status stopping=""
    shift

    # Ask the daemon to stop, but leave the loop to observe it exiting, so that
    # shutdown is ordered and the exit status still gets logged.
    trap 'stopping=1
          if [[ -n $child ]]; then log "stopping $name"; kill "$child" 2>/dev/null; fi' TERM INT

    while [[ -z $stopping ]]; do
        rm -rf "$dir"
        mkdir -p "$dir"

        log "starting $name: $*"
        started=$SECONDS
        "$@" </dev/null &
        child=$!
        status=0
        wait "$child" || status=$?

        # wait returns as soon as a trapped signal arrives, while the daemon is
        # still shutting down, so keep waiting until it has actually exited.
        while kill -0 "$child" 2>/dev/null; do
            status=0
            wait "$child" || status=$?
        done

        child=""
        log "$name exited ($status)"

        # Back off so we don't spin in case of a broken binary or similar issue.
        if [[ -z $stopping ]] && (( SECONDS - started < 2 )); then
            sleep 2
        fi
    done
}

cd /
mkdir -p "$ROOT"
publish_interfaces

pids=()
supervise hostapd hostapd -t -g "$ROOT/hostapd/global" &
pids+=("$!")
supervise wpa_supplicant wpa_supplicant -t -g "$ROOT/wpa_supplicant/global" &
pids+=("$!")

trap 'kill "${pids[@]}" 2>/dev/null' TERM INT
log "ready"

# wait may return early when a trapped signal arrives;
# keep waiting until every supervisor has finished stopping its daemon.
while ! wait; do :; done

# The file only describes radios this fixture holds, so it should not outlive the
# daemons: a run that starts no fixture would otherwise find one to read. That
# leaves a killed container publishing radios nobody owns, which is why a client
# has to reach the control socket before believing any of this.
rm -f "$ROOT/interfaces"
log "stopped"
