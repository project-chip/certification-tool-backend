<!--
Copyright (c) 2026 Project CHIP Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# CSA Certification Tool - Wi-Fi Fixture

A Wi-Fi radio component for the Matter Test Harness. It owns one or more Wi-Fi
devices (usually USB dongles) and runs [hostap](https://w1.fi/hostap.git)
(hostapd / wpa_supplicant) so the harness can play either the Access Point
or Station role a particular test needs.

The host's builtin interface should not be used with the Wi-Fi Fixture -- it is
usually managed by the host OS (e.g. systemd-networkd) and is left available for
the TH operator to use manually as needed.

The container builds hostap with a number of patches that implement support for
Matter Per-Device Credentials authentication.

## How the harness runs it

A run asks for the fixture by naming the interfaces it owns in the project
configuration, under `network.wifi.interfaces`. The backend starts the container
for the duration of a test suite, passing those names in `WIFI_FIXTURE_IFNAMES`,
and stops it again during suite cleanup.

That is the whole of the harness side. The container accepts no commands of its
own: it starts both daemons, publishes the interfaces it claimed, and restarts a
daemon that exits. Everything else is driven by the tests over the control
sockets.

The container is privileged and shares the host's network namespace, so it can
see every radio on the machine, including the host's own. Naming the fixture's
interfaces explicitly, rather than discovering them, is what keeps a test off
the host's radio. An interface that is missing or is not a wireless device stops
the container at startup, rather than surfacing later as a confusing test
failure.

## Control interface

Everything the tests do to the fixture goes through the daemons' control
sockets, in a single bind-mounted directory. DBus is not used: hostapd has no
DBus interface at all, and wpa_supplicant's `fi.w1.wpa_supplicant1` service is
a compile-time well-known name that is usually already claimed by the supplicant
instance managed by the host OS. Both daemons expose a global control socket
that does everything needed, so that is the single mechanism used for both.

```
/run/wifi-fixture/          bind-mounted into the fixture and SDK containers
  interfaces                Wi-Fi interfaces used by the fixture
  hostapd/
    global                  hostapd global control socket
    <ifname>                per-interface control socket
    ...                     configuration files created by tests
  wpa_supplicant/
    global
    <ifname>                per-interface control socket
    ...                     configuration files created by tests
```

The directory is always mounted as `/run/wifi-fixture`, on the host as well as
in every container: control socket traffic carries paths, and they have to
resolve to the same files on both ends. The path is also compiled into the
binaries as `CONFIG_CTRL_IFACE_DIR`, one subtree per daemon, so the CLIs need no
`-p`.

Both daemons run for the life of the container and start with no interface
attached. A test attaches one of the fixture's interfaces to hostapd or to
wpa_supplicant as it needs, writing any configuration files that daemon requires
into its subtree. `interfaces` carries one `<ifname> <phy>` record per line,
listing what the fixture claimed:

```
wlan1 phy1
wlan2 phy2
```

The phy is what hostapd's `ADD bss_config=<phy>:<conf>` needs, and only this
container can see `/sys` to resolve it. Note that a phy index follows
enumeration order rather than the device, so the published value holds only for
as long as that radio stays plugged in; restart the container after swapping or
reconnecting a dongle.

### Teardown

A test releases an interface by removing it from the daemon holding it, or
resets a daemon entirely by sending `TERMINATE` to its global socket. The
supervisor then wipes that daemon's subtree, including any configuration files
tests left in it, and starts the daemon again. Tests wait for the global socket
to reappear and answer `PING`. Note that `TERMINATE` resets every interface that
daemon holds, not just the caller's, which is fine as long as the harness runs
tests serially.

Note also that `interfaces` is removed when the container stops, but a killed
container leaves it behind. Reaching a global control socket is therefore what
tells a test it has a fixture; the file only says which radios it has.

## Running it by hand

The daemons come up with no interface attached, so the container can be started
once and driven by hand while developing a test. Note that the backend removes
any container it finds for this image when a run starts, so it will take one
started by hand away with it.

```sh
docker run --rm -d --name certification-tool-wifi --privileged --network host \
    -e WIFI_FIXTURE_IFNAMES=wlan1 \
    -v /run/wifi-fixture:/run/wifi-fixture \
    ghcr.io/project-chip/csa-certification-tool-wifi:latest

docker exec -it certification-tool-wifi hostapd_cli -i global ping
docker exec -it certification-tool-wifi wpa_cli -i global ping
docker exec -it certification-tool-wifi hostapd_cli -i global raw INTERFACES
```

Run the CLIs inside the container: a control client binds its *own* socket for
the daemon to reply to, and by default that lands somewhere the daemon cannot
see, so a client on the host hangs until its timeouts expire.

The global socket is addressed as an interface named `global`. Note that
`hostapd_cli` has no commands of its own for the global socket, so those go
through `raw`, which passes the command through verbatim. Note also that hostapd
logs nothing at startup while it holds no interface, so `ping` is the only sign
it is alive.

## Building the image

Use `scripts/build-docker-image.sh`, as for the other Test Harness images. The
hostap revision is pinned in the Dockerfile, and the patches in `patches/` are
applied over it in sorted order.
