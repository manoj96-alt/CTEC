# Local Development Guide

Run the complete system with `docker compose up --build`. Use `make lint`, `make typecheck`, and `make test` before submitting changes. Stop it with `docker compose down`; add `--volumes` only when intentionally discarding local PostgreSQL data.

