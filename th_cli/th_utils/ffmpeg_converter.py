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
import queue
import subprocess
import threading
from pathlib import Path
from typing import Optional

import click
from loguru import logger


class FFmpegStreamConverter:
    """Converts H.264 raw stream to MP4 in real-time using FFmpeg."""

    def __init__(self):
        self.ffmpeg_process = None
        self.output_queue = queue.Queue()

    def start_conversion(self):
        """Start FFmpeg process for real-time conversion."""
        try:
            # FFmpeg command to convert H.264 raw input to MP4 output
            cmd = [
                "ffmpeg",
                "-f",
                "h264",  # Input format: H.264 raw
                "-i",
                "pipe:0",  # Read from stdin
                "-c:v",
                "copy",  # Copy video stream (no re-encoding)
                "-f",
                "mp4",  # Output format: MP4
                "-movflags",
                "frag_keyframe+empty_moov",  # Enable streaming
                "pipe:1",  # Write to stdout
            ]

            self.ffmpeg_process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Start thread to read FFmpeg output
            threading.Thread(target=self._read_ffmpeg_output, daemon=True).start()

            logger.info("FFmpeg converter started successfully")
            return True

        except FileNotFoundError:
            logger.error("FFmpeg not found - raw H.264 streaming only")
            return False
        except Exception as e:
            logger.error(f"Failed to start FFmpeg converter: {e}")
            return False

    def _read_ffmpeg_output(self):
        """Read converted MP4 data from FFmpeg stdout."""
        try:
            while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                data = self.ffmpeg_process.stdout.read(8192)
                if data:
                    try:
                        self.output_queue.put_nowait(data)
                    except queue.Full:
                        pass  # Drop frames if queue is full
        except Exception as e:
            logger.error(f"Error reading FFmpeg output: {e}")

    def feed_data(self, h264_data: bytes):
        """Feed H.264 raw data to FFmpeg for conversion."""
        if self.ffmpeg_process and self.ffmpeg_process.stdin:
            try:
                self.ffmpeg_process.stdin.write(h264_data)
                self.ffmpeg_process.stdin.flush()
            except Exception as e:
                logger.error(f"Error feeding data to FFmpeg: {e}")

    def get_converted_data(self, timeout=1.0):
        """Get converted MP4 data."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Stop FFmpeg conversion."""
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")
            finally:
                self.ffmpeg_process = None


class VideoFileConverter:
    """Handles conversion of video files using FFmpeg."""

    @staticmethod
    def convert_video_to_mp4(bin_file_path: Path) -> Optional[Path]:
        """Convert .bin video file to .mp4 using ffmpeg if available."""
        try:
            # Check if ffmpeg is available
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                click.echo("❌ FFmpeg not available for conversion")
                return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            click.echo("❌ FFmpeg not found - install with: brew install ffmpeg")
            return None

        try:
            # Create MP4 filename
            mp4_file = bin_file_path.with_suffix(".mp4")
            click.echo(f"🔄 Converting {bin_file_path.name} to MP4...")

            # Enhanced FFmpeg command for H.264 raw stream conversion
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite existing files
                "-f",
                "h264",  # Input format: H.264 raw
                "-i",
                str(bin_file_path),  # Input file
                "-c:v",
                "libx264",  # Re-encode with libx264 (more compatible)
                "-preset",
                "fast",  # Fast encoding preset
                "-crf",
                "23",  # Constant rate factor (good quality)
                "-pix_fmt",
                "yuv420p",  # Pixel format (widely compatible)
                "-movflags",
                "+faststart",  # Move metadata to beginning for web streaming
                "-r",
                "30",  # Set frame rate to 30fps
                str(mp4_file),  # Output file
            ]

            click.echo(f"🎬 Running: {' '.join(cmd[:8])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and mp4_file.exists():
                file_size = mp4_file.stat().st_size
                click.echo(f"✅ Video converted to MP4: {mp4_file} ({file_size:,} bytes)")

                # Try alternative conversion if first attempt creates very small file
                if file_size < 1024:  # Less than 1KB suggests problem
                    click.echo("⚠️  Small output file, trying alternative conversion...")
                    return VideoFileConverter._try_alternative_conversion(bin_file_path, mp4_file)

                return mp4_file
            else:
                click.echo(f"❌ FFmpeg conversion failed:")
                click.echo(f"   Return code: {result.returncode}")
                if result.stderr:
                    # Show only relevant error lines
                    error_lines = [
                        line
                        for line in result.stderr.split("\n")
                        if "error" in line.lower() or "invalid" in line.lower()
                    ]
                    for line in error_lines[:3]:  # Show max 3 error lines
                        click.echo(f"   {line.strip()}")

                # Try alternative conversion method
                return VideoFileConverter._try_alternative_conversion(bin_file_path, mp4_file)

        except subprocess.TimeoutExpired:
            click.echo("❌ FFmpeg conversion timed out (>60 seconds)")
            return None
        except Exception as e:
            click.echo(f"❌ Video conversion error: {e}")
            return None

    @staticmethod
    def _try_alternative_conversion(bin_file_path: Path, mp4_file: Path) -> Optional[Path]:
        """Try alternative FFmpeg conversion methods."""
        alternative_methods = [
            {
                "name": "Raw H.264 with container fix",
                "cmd": [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "h264",
                    "-i",
                    str(bin_file_path),
                    "-c:v",
                    "copy",
                    "-bsf:v",
                    "h264_mp4toannexb",  # Fix stream format
                    str(mp4_file),
                ],
            },
            {
                "name": "Force framerate and format",
                "cmd": [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "h264",
                    "-r",
                    "25",  # Input framerate
                    "-i",
                    str(bin_file_path),
                    "-c:v",
                    "libx264",
                    "-r",
                    "25",  # Output framerate
                    "-pix_fmt",
                    "yuv420p",
                    str(mp4_file),
                ],
            },
            {
                "name": "Raw video with size assumption",
                "cmd": [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "rawvideo",
                    "-pixel_format",
                    "yuv420p",
                    "-video_size",
                    "640x480",
                    "-r",
                    "30",
                    "-i",
                    str(bin_file_path),
                    "-c:v",
                    "libx264",
                    str(mp4_file),
                ],
            },
        ]

        for method in alternative_methods:
            try:
                click.echo(f"🔄 Trying: {method['name']}")
                result = subprocess.run(method["cmd"], capture_output=True, text=True, timeout=30)

                if result.returncode == 0 and mp4_file.exists() and mp4_file.stat().st_size > 1024:
                    file_size = mp4_file.stat().st_size
                    click.echo(f"✅ Success with {method['name']}: {mp4_file} ({file_size:,} bytes)")
                    return mp4_file

            except Exception as e:
                click.echo(f"   Failed: {e}")
                continue

        click.echo("❌ All conversion methods failed")
        click.echo(f"💡 You can try manual conversion:")
        click.echo(f"   ffmpeg -f h264 -i '{bin_file_path}' -c:v libx264 '{bin_file_path.with_suffix('.mp4')}'")
        return None
