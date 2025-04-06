#!/bin/sh

uv sync || exit 1
git add uv.lock || exit 1
