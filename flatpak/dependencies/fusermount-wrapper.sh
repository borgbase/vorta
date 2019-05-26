#!/bin/sh

if [ -z "$_FUSE_COMMFD" ]; then
    FD_ARGS=
else
    FD_ARGS="--env=_FUSE_COMMFD=${_FUSE_COMMFD} --forward-fd=${_FUSE_COMMFD}"
fi

exec flatpak-spawn --host --forward-fd=1 --forward-fd=2 --forward-fd=3 $FD_ARGS fusermount "$@"
