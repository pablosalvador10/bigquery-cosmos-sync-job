---
description: Security and configuration patterns. Use when handling secrets, environment variables, authentication, Azure credentials, CORS, or Key Vault.
---

# Security & Configuration

## Environment Variables
- Local: `.env.example` — copy to `.env` for development.
- Cloud: `.env.azure.example` — production configuration template.
- Use `pydantic-settings` (`AppSettings`) — never read `os.environ` directly.
- `AppSettings` extends `FoundrySettings` for layered config.

## Secret Management
- **Never commit secrets, tokens, or connection strings.**
- Local dev: `.env` file (gitignored).
- Production: Azure Key Vault references or Container App secrets.
- `FOUNDRY_CREDENTIAL_MODE`:
  - `dev` → `DefaultAzureCredential` (local dev, uses `az login`).
  - `managed_identity` → `ManagedIdentityCredential` (production Container Apps).

## CORS
- `CORS_ORIGINS` env var controls allowed origins.
- Default: `http://localhost:5173` (Vite dev server).
- Production: set to actual frontend URL.

## Cosmos DB Security
- Uses `DefaultAzureCredential` — no connection string needed.
- Parameterized queries only — never string-interpolate user input.
- Partition key `/session_id` provides tenant isolation.

## OpenTelemetry
- `OTEL_EXPORTER` controls destination: `console` (dev), `otlp` (collector), `azure` (App Insights).
- `APPLICATIONINSIGHTS_CONNECTION_STRING` for Azure Monitor integration.
- Tool calls auto-traced via `ToolRegistry` OpenTelemetry spans.
