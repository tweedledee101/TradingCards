# Facebook Marketplace Intake (NovaAct)

This module is the starting point for automating Facebook Marketplace intake using NovaAct.

## Configuration
Set the NovaAct API key in an environment variable:

```bash
export NOVAACT_API_KEY="your-key-here"
```

Optional:

```bash
export NOVAACT_BASE_URL="https://api.novaact.example"
```

## Next Steps
- Wire in the NovaAct SDK or HTTP client calls for:
  - Authentication
  - Browser/session initialization
  - Facebook login
  - Marketplace search
- Save normalized listing data into the acquisition pipeline intake schema.

## Notes
- Do **not** commit secrets. Use environment variables or local `.env` files (ignored by git).
