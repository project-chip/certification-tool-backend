#!/usr/bin/env bash

#
# Copyright (c) 2020 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

ME=$(basename "$0")
ROOT_DIR=$(realpath $(dirname "$0")/..)
cd $ROOT_DIR

DEFAULT_IMAGE=csa-certification-tool-backend


GHCR_ORG="ghcr.io"
ORG=${DOCKER_BUILD_ORG:-project-chip}

# Latest commit hash
GIT_SHA=$(git rev-parse --short HEAD)

# If working copy has changes, append `-local` to hash
GIT_DIFF=$(git diff -s --exit-code || echo "-local")
if [[ $GIT_DIFF ]]; then
  echo "  🔴 Git repo has changes. Please commit all changes before publishing."
fi
GIT_REV=$GIT_SHA$GIT_DIFF
echo "$GIT_REV"


IMAGE=${DOCKER_BUILD_IMAGE:-$DEFAULT_IMAGE}

# version
VERSION=${DOCKER_BUILD_VERSION:-$GIT_REV}

# verify that repo is clean
DIRTY=`git status --porcelain --untracked-files=no`


# help
[[ ${*/--help//} != "${*}" ]] && {
    set +x
    echo "Usage: $me <OPTIONS>

  Build and (optionally tag as latest, push) a docker image from Dockerfile in CWD

  Options:
   --no-cache   passed as a docker build argument
   --latest     update latest to the current built version (\"$VERSION\")
   --push       push image(s) to ghcr.io (requires docker login for \"$ORG\")
   --skip-build skip the build/prune step
   --help       get this message
   --squash     squash docker layers before push them to docker.io (requires docker-squash python module)

"
    exit 0
}

die() {
    echo "$me: *** ERROR: $*"
    exit 1
}

set -ex

[[ -n $VERSION ]] || die "version cannot be empty"

BUILD_ARGS=()
if [[ ${*/--no-cache//} != "${*}" ]]; then
    BUILD_ARGS+=(--no-cache)
fi

# Don't run `docker build` and `docker image prune` when `--skip-build` in arguments
[[ ${*/--skip-build//} != "${*}" ]] || {
    docker build "${BUILD_ARGS[@]}" --build-arg TARGETPLATFORM="$TARGET_PLATFORM_TYPE"  --build-arg GIT_SHA="$GIT_REV" --build-arg VERSION="$VERSION" -t "$GHCR_ORG/$ORG/$IMAGE:$VERSION" .
    docker image prune --force
}

[[ ${*/--latest//} != "${*}" ]] && {
    docker tag "$GHCR_ORG"/"$ORG"/"$IMAGE":"$VERSION" "$GHCR_ORG"/"$ORG"/"$IMAGE":latest
}

[[ ${*/--squash//} != "${*}" ]] && {
    command -v docker-squash >/dev/null &&
        docker-squash "$GHCR_ORG"/"$ORG"/"$IMAGE":"$VERSION" -t "$GHCR_ORG"/"$ORG"/"$IMAGE":latest
}

[[ ${*/--push//} != "${*}" ]] && {
    if [[ $GIT_DIFF ]]; then
        die "Don't push image with local changes"
    fi
    docker push "$GHCR_ORG"/"$ORG"/"$IMAGE":"$VERSION"
    [[ ${*/--latest//} != "${*}" ]] && {
        docker push "$GHCR_ORG"/"$ORG"/"$IMAGE":latest
    }
}

[[ ${*/--clear//} != "${*}" ]] && {
    docker rmi -f "$GHCR_ORG"/"$ORG"/"$IMAGE":"$VERSION"
    [[ ${*/--latest//} != "${*}" ]] && {
        docker rmi -f "$GHCR_ORG"/"$ORG"/"$IMAGE":latest
    }
}

docker images --filter=reference="$GHCR_ORG/$ORG/*"