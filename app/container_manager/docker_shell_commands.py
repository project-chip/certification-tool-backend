#
# Copyright (c) 2025 Project CHIP Authors
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
"""
Utility functions to generate shell command equivalents for Docker API operations.
Useful for debugging and understanding what Docker operations are being performed.
"""
from pathlib import Path
from typing import Dict, List, Union

# Log message constants
SHELL_CMD_LOG_PREFIX = "Docker API call equivalent shell command:\n"

# Shell special characters that require escaping
SHELL_SPECIAL_CHARS = [
    " ",
    "'",
    '"',
    "$",
    "`",
    "\\",
    "!",
    "&",
    "|",
    ";",
    "(",
    ")",
    "<",
    ">",
]


def escape_shell_arg(arg: str) -> str:
    """
    Escape shell argument if it contains spaces or special characters.

    Uses single-quote wrapping for safety. Any single quotes in the argument
    are escaped using the pattern: ' becomes '\'' (close quote, escaped quote, open quote).

    Returns:
        The argument wrapped in single quotes if it contains special characters,
        otherwise returns the argument unchanged.
    """
    if any(c in arg for c in SHELL_SPECIAL_CHARS):
        # Escape any single quotes: ' becomes '\''
        escaped_arg = arg.replace("'", "'\\''")
        # Wrap the entire argument in single quotes
        return f"'{escaped_arg}'"
    return arg


def docker_run_command(image_tag: str, parameters: Dict) -> str:
    """
    Generate docker run command from API parameters.

    Args:
        image_tag: Docker image tag
        parameters: Dictionary of parameters passed to docker.containers.run()

    Returns:
        String representation of equivalent shell command
    """
    cmd_parts = ["docker run"]

    # Handle privileged mode
    if parameters.get("privileged"):
        cmd_parts.append("--privileged")

    # Handle detach mode
    if parameters.get("detach"):
        cmd_parts.append("-d")

    # Handle network
    if network := parameters.get("network"):
        cmd_parts.append(f"--network {escape_shell_arg(network)}")

    # Handle name
    if name := parameters.get("name"):
        cmd_parts.append(f"--name {escape_shell_arg(name)}")

    # Handle volumes
    if volumes := parameters.get("volumes"):
        for host_path, mount_config in volumes.items():
            bind_path = mount_config.get("bind")
            mode = mount_config.get("mode", "rw")
            volume_spec = f"{host_path}:{bind_path}:{mode}"
            cmd_parts.append(f"-v {escape_shell_arg(volume_spec)}")

    # Handle environment variables
    if environment := parameters.get("environment"):
        if isinstance(environment, dict):
            for key, value in environment.items():
                env_spec = f"{key}={value}"
                cmd_parts.append(f"-e {escape_shell_arg(env_spec)}")
        elif isinstance(environment, list):
            for env_var in environment:
                cmd_parts.append(f"-e {escape_shell_arg(env_var)}")

    # Handle working directory
    if working_dir := parameters.get("working_dir"):
        cmd_parts.append(f"-w {escape_shell_arg(working_dir)}")

    # Handle ports
    if ports := parameters.get("ports"):
        if isinstance(ports, dict):
            for container_port, host_config in ports.items():
                if isinstance(host_config, list):
                    for host_port_config in host_config:
                        host_port = host_port_config.get("HostPort")
                        port_spec = f"{host_port}:{container_port}"
                        cmd_parts.append(f"-p {escape_shell_arg(port_spec)}")
                elif isinstance(host_config, tuple):
                    host_ip, host_port = host_config
                    port_spec = f"{host_ip}:{host_port}:{container_port}"
                    cmd_parts.append(f"-p {escape_shell_arg(port_spec)}")
                else:
                    port_spec = f"{host_config}:{container_port}"
                    cmd_parts.append(f"-p {escape_shell_arg(port_spec)}")

    # Handle user
    if user := parameters.get("user"):
        cmd_parts.append(f"--user {escape_shell_arg(user)}")

    # Handle stdin_open
    if parameters.get("stdin_open"):
        cmd_parts.append("-i")

    # Handle tty
    if parameters.get("tty"):
        cmd_parts.append("-t")

    # Add image tag
    cmd_parts.append(escape_shell_arg(image_tag))

    # Handle command
    if command := parameters.get("command"):
        if isinstance(command, list):
            cmd_parts.extend([escape_shell_arg(str(c)) for c in command])
        else:
            # For string commands, use sh -c to properly execute the command
            cmd_parts.extend(["sh", "-c", escape_shell_arg(str(command))])

    return " ".join(cmd_parts)


def docker_exec_command(
    container_name: str,
    command: Union[str, List[str]],
    stdin: bool = False,
    detach: bool = False,
) -> str:
    """
    Generate docker exec command from API parameters.

    Args:
        container_name: Name or ID of the container
        command: Command to execute (string or list)
        stdin: Whether stdin is enabled
        detach: Whether to run in detached mode

    Returns:
        String representation of equivalent shell command
    """
    cmd_parts = ["docker exec"]

    if stdin:
        cmd_parts.append("-i")

    if detach:
        cmd_parts.append("-d")

    cmd_parts.append(escape_shell_arg(container_name))

    if isinstance(command, list):
        cmd_parts.extend([escape_shell_arg(str(c)) for c in command])
    else:
        # Command is already a full string, use sh -c to execute it
        cmd_parts.extend(["sh", "-c", escape_shell_arg(str(command))])

    return " ".join(cmd_parts)


def docker_kill_command(container_name: str) -> str:
    """
    Generate docker kill command.

    Args:
        container_name: Name or ID of the container

    Returns:
        String representation of equivalent shell command
    """
    return f"docker kill {escape_shell_arg(container_name)}"


def docker_rm_command(container_name: str, force: bool = False) -> str:
    """
    Generate docker rm command.

    Args:
        container_name: Name or ID of the container
        force: Whether to force remove

    Returns:
        String representation of equivalent shell command
    """
    cmd = "docker rm"
    if force:
        cmd += " -f"
    cmd += f" {escape_shell_arg(container_name)}"
    return cmd


def docker_cp_from_container_command(
    container_name: str,
    container_path: Path,
    host_path: Path,
) -> str:
    """
    Generate docker cp command for copying from container to host.

    Args:
        container_name: Name or ID of the container
        container_path: Path inside the container
        host_path: Destination path on host

    Returns:
        String representation of equivalent shell command
    """
    source = f"{container_name}:{container_path}"
    return f"docker cp {escape_shell_arg(source)} {escape_shell_arg(str(host_path))}"


def docker_cp_to_container_command(
    container_name: str,
    host_path: Path,
    container_path: Path,
) -> str:
    """
    Generate docker cp command for copying from host to container.

    Args:
        container_name: Name or ID of the container
        host_path: Source path on host
        container_path: Destination path inside the container

    Returns:
        String representation of equivalent shell command
    """
    destination = f"{container_name}:{container_path}"
    return (
        f"docker cp {escape_shell_arg(str(host_path))} {escape_shell_arg(destination)}"
    )
