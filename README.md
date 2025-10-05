# GitLab MR Review

GitLab MR Review automates merge-request code reviews with AI providers including Google Gemini, Anthropic Claude, and OpenAI. It ingests GitLab MR diffs, produces inline comments plus a summary, and posts them back through the GitLab API. The repository ships with local tooling, metrics, and deployment scripts so you can run the reviewer from your laptop or as a serverless function.

## Local development

### Requirements

- Python 3.8 or newer (3.11 matches the managed runtimes used in deployment scripts)
- `pip` or `uv`
- Make (for the provided automation targets)

### Setup

```bash
git clone <your-repo-url>
cd gitlab-mr-review

# Create and activate a virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install the package and development tooling
make dev

# Create `.env` from the template and populate credentials
make init
vi .env
```

### Environment variables

Define the following in `.env` or export them in your shell before running the reviewer:

| Variable | Purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Google Gemini API key (required unless you only use another provider) |
| `ANTHROPIC_API_KEY` | Anthropic Claude key (optional) |
| `OPENAI_API_KEY` | OpenAI API key (optional) |
| `GITLAB_TOKEN` | GitLab personal access token with `api` scope (required) |
| `GITLAB_URL` | Optional GitLab instance URL (defaults to `https://gitlab.com`) |
| `AI_MODEL` | Default provider (`gemini`, `claude`, `openai`), defaults to `gemini` |

### Running reviews locally

Interactive workflow:

```bash
make test-local
```

You will be prompted for the project ID, MR IID, GitLab URL, and model choice. The script resolves the selected model via the central registry (`gitlab_mr_review.ai_models`) and executes `gitlab_mr_review.main`.

Scripted run (useful for CI or non-interactive environments):

```bash
python3 scripts/test_local.py \
  --project-id 12345 \
  --mr-iid 1 \
  --ai-model gemini \
  --model-name gemini-2.5-flash
```

Both paths run the same review pipeline and print the response payload returned by the core reviewer.

### Tests and quality gates

```bash
make test        # pytest
make check       # black --check, flake8, mypy
make format      # apply black formatting
```

Manual equivalents:

```bash
pytest -q --cov=gitlab_mr_review
black gitlab_mr_review/ scripts/ test_local.py --check
flake8 gitlab_mr_review/ --max-line-length=100
mypy gitlab_mr_review/
```

### Makefile reference

| Command | Description |
| --- | --- |
| `make dev` | Install editable package and dev dependencies |
| `make init` | Copy `.env.example` to `.env` |
| `make check-env` | Print which API keys/tokens are currently configured |
| `make test-local` | Interactive local review targeting a GitLab MR |
| `make deploy` | Interactive deploy chooser (GCP / AWS / DigitalOcean) |
| `make clean` | Remove caches and build artefacts |

## Cloud function deployment

### Google Cloud Functions

#### Prerequisites (GCP)

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Export at least one AI provider key (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`)
- Optional overrides: `FUNCTION_NAME`, `GCP_REGION`, `MEMORY`, `TIMEOUT`

#### Deploy (GCP)

```bash
make deploy-gcp
# or
cd cloud_functions/gcp
./deploy.sh
```

The script copies `gitlab_mr_review/` next to `main.py`, installs `cloud_functions/gcp/requirements.txt`, and deploys with entry point `gitlab_mr_review_http`. Any detected API keys are passed with `--set-env-vars`.

### DigitalOcean Functions

#### Prerequisites (DigitalOcean)

- `doctl` CLI installed and authenticated (`doctl auth init`)
- `GOOGLE_API_KEY` exported (Gemini is the default provider packaged for this function)

#### Deploy (DigitalOcean)

```bash
make deploy-digitalocean
# or
cd cloud_functions/digitalocean
./deploy.sh
```

The script stages a serverless bundle, writes a `.env` for the remote build, and prints the deployed function URL. Use that URL for GitLab webhooks or manual triggers.

## Additional resources

- `gitlab_mr_review/main.py` – Orchestrates GitLab API calls, comment formatting, and adapter selection.
- `gitlab_mr_review/ai_models.py` – Central registry for model metadata, pricing, and selection helpers.
- `scripts/select_model.py` – Interactive model chooser used by `make test-local`.
- `cloud_functions/*/deploy.sh` – Provider-specific deployment automation.

## Suggested workflow

1. Modify code under `gitlab_mr_review/`.
2. Run `make check && make test` to keep quality gates green.
3. Validate the change against a staging MR with `make test-local`.
4. Commit and open your merge request.
