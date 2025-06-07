#!/bin/bash
# Fix esbuild binary permissions
find .yarn/unplugged -name esbuild -type f -exec chmod +x {} \; 2>/dev/null || true
echo "✅ Fixed esbuild permissions"