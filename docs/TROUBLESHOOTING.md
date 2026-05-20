# Troubleshooting

## Frontend cannot reach backend
- Verify backend is on `http://localhost:8001`.
- Check Vite proxy config in `ts/apps/ui-copilot-template/vite.config.ts`.

## SSE stream appears stuck
- Confirm endpoint is `POST /api/v1/chat/stream`.
- Ensure response `content-type` is `text/event-stream`.

## Cosmos mode fails
- Ensure `STORAGE_MODE=cosmos` and `COSMOS_ENDPOINT` are set.
- Verify managed identity or credentials for Cosmos access.

## Terraform apply fails on naming
- Resource names are derived from `environment_name` + hash suffix.
- Cosmos account names must be globally unique — check `local.names.cosmos` in `infra/main.tf`.
