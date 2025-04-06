#!/bin/sh

uv run clickusagemd run || exit 1
git add USAGE.md || exit 1

uv sync || exit 1
git add uv.lock || exit 1
