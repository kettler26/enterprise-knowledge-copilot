# Cloudflare Worker deploy template

This worker forwards requests from Cloudflare edge to your API.

## Quick start

1. Install Wrangler (`npm i -g wrangler`)
2. Set `COPILOT_API_BASE_URL` in `wrangler.toml`
3. Deploy:

```bash
wrangler deploy
```
# Cloudflare Worker proxy template

Use this Worker as a thin edge proxy in front of your API service.

## Setup

1. Install Wrangler:
   - `npm i -g wrangler`
2. Edit `wrangler.toml`:
   - set `COPILOT_API_BASE_URL` to your deployed API URL
3. Deploy:
   - `wrangler deploy`

This template forwards all paths to the API and keeps auth headers (`x-api-key` or `Authorization`) intact.
