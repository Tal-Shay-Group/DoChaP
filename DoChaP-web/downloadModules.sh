#!/bin/bash
# Installs the server-side node modules. Run from the DoChaP-web project root.

set -e

# `npm ci` rather than `npm i`: it installs package-lock.json verbatim and
# fails if the lock and package.json have drifted, whereas `npm i` may quietly
# resolve newer versions and rewrite the lock. node_modules/ is gitignored and
# rebuilt on every deploy, so this is what keeps the security-patched versions
# in the lockfile pinned on the server.
npm ci
