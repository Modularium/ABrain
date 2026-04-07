# FlowiseHub Publishing Guide

This document explains how to publish the ABrain Flowise plugin to FlowiseHub or any compatible registry.

## Preparation

1. Generate the plugin manifest:
   ```bash
   python tools/generate_flowise_plugin.py
   ```
2. Validate the manifest locally:
   ```bash
   python tools/validate_plugin_manifest.py
   ```
3. Package the nodes and manifest:
   ```bash
   python tools/package_plugin.py --output agentnn_flowise_plugin.zip
   ```

The archive contains the compiled JavaScript files, node definitions and `flowise-plugin.json`.

## Repository and Release

Tag a GitHub release to provide a stable download link. The repository URL is
https://github.com/EcoSphereNetwork/Agent-NN. GitHub Pages can host a preview page under `dist/index.html` with screenshots and usage instructions.

## Submitting to FlowiseHub

Upload the generated archive or reference the release page in FlowiseHub. Ensure that `flowise-plugin.json` includes the fields `repository`, `homepage` and `license` so that users can verify the source and terms.
