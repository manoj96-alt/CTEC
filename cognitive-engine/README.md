# Cognitive Engine

This directory contains the existing CTEC cognitive implementation, including the backend capabilities delivered by CDD-004 through CDD-009, the prototype frontend, deployment support, scripts, and reusable engineering tools.

The relocation changes repository paths only. It does not change the Canonical Enterprise Ontology, business capability semantics, architecture layers, or runtime package imports. Python continues to run from `cognitive-engine/backend`, where `app` remains the package root.

Repository-wide build and development commands are exposed by the root `Makefile` and `docker-compose.yml`.
