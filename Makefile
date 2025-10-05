.PHONY: help install load-env install-dev delete-comments format test-local deploy

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)GitLab MR Review - Makefile Commands$(NC)'
	@echo ''
	@echo '$(GREEN)Usage: make [target]$(NC)'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Installation targets

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -r requirements-dev.txt
	pip install -e .
	@echo "$(GREEN)✓ Development environment ready$(NC)"

## Code Quality targets

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	black gitlab_mr_review/ test_local.py --line-length=100
	@echo "$(GREEN)✓ Code formatted$(NC)"

## Testing targets

test-local: ## Run local integration test (interactive)
	@echo "$(BLUE)GitLab MR Review - Local Test$(NC)"
	@echo ""
	@if [ -f .env ]; then \
		echo "$(GREEN)Loading environment from .env file...$(NC)"; \
		export $$(cat .env | grep -v '^#' | grep -v '^$$' | xargs); \
	fi; \
	if [ -z "$$GOOGLE_API_KEY" ] && [ -z "$$ANTHROPIC_API_KEY" ] && [ -z "$$OPENAI_API_KEY" ]; then \
		echo "$(RED)Error: No API key found$(NC)"; \
		echo "Set at least one: GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY"; \
		echo "Edit your .env file or run: make init"; \
		exit 1; \
	fi; \
	if [ -z "$$GITLAB_TOKEN" ]; then \
		echo "$(RED)Error: GITLAB_TOKEN not set$(NC)"; \
		echo "Edit your .env file or run: export GITLAB_TOKEN=your-token"; \
		exit 1; \
	fi; \
	if [ -z "$$GITLAB_URL" ]; then \
		read -p "GitLab URL (default: https://gitlab.com): " gitlab_url; \
		export GITLAB_URL=$${gitlab_url:-https://gitlab.com}; \
	fi; \
	read -p "Project ID: " project_id; \
	read -p "MR IID: " mr_iid; \
	export PROJECT_ID=$$project_id; \
	export MR_IID=$$mr_iid; \
	echo ""; \
	echo "$(YELLOW)Select AI Provider:$(NC)"; \
	echo "  1) Gemini (Google)"; \
	echo "  2) Claude (Anthropic)"; \
	echo "  3) OpenAI"; \
	read -p "Enter choice [1-3]: " provider_choice; \
	case $$provider_choice in \
		1) \
			export AI_MODEL=gemini; \
			echo ""; \
			echo "$(YELLOW)Select Gemini Model:$(NC)"; \
			MODEL_SELECTION=$$(python scripts/select_model.py gemini); \
			if [ -z "$$MODEL_SELECTION" ]; then \
				echo "$(RED)Failed to select Gemini model$(NC)"; \
				exit 1; \
			fi; \
			export MODEL_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f1); \
			MODEL_DISPLAY_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f2-); \
			export MODEL_DISPLAY_NAME; \
		;; \
		2) \
			export AI_MODEL=claude; \
			echo ""; \
			echo "$(YELLOW)Select Claude Model:$(NC)"; \
			MODEL_SELECTION=$$(python scripts/select_model.py claude); \
			if [ -z "$$MODEL_SELECTION" ]; then \
				echo "$(RED)Failed to select Claude model$(NC)"; \
				exit 1; \
			fi; \
			export MODEL_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f1); \
			MODEL_DISPLAY_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f2-); \
			export MODEL_DISPLAY_NAME; \
		;; \
		3) \
			export AI_MODEL=openai; \
			echo ""; \
			echo "$(YELLOW)Select OpenAI Model:$(NC)"; \
			MODEL_SELECTION=$$(python scripts/select_model.py openai); \
			if [ -z "$$MODEL_SELECTION" ]; then \
				echo "$(RED)Failed to select OpenAI model$(NC)"; \
				exit 1; \
			fi; \
			export MODEL_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f1); \
			MODEL_DISPLAY_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f2-); \
			export MODEL_DISPLAY_NAME; \
		;; \
		*) \
			echo "$(RED)Invalid choice, using default (Gemini)$(NC)"; \
			export AI_MODEL=gemini; \
			MODEL_SELECTION=$$(python scripts/select_model.py gemini); \
			if [ -z "$$MODEL_SELECTION" ]; then \
				echo "$(RED)Failed to select default Gemini model$(NC)"; \
				exit 1; \
			fi; \
			export MODEL_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f1); \
			MODEL_DISPLAY_NAME=$$(echo "$$MODEL_SELECTION" | cut -d'|' -f2-); \
			export MODEL_DISPLAY_NAME; \
	esac; \
	if [ -z "$$MODEL_DISPLAY_NAME" ]; then \
		MODEL_DISPLAY_NAME=$$MODEL_NAME; \
		export MODEL_DISPLAY_NAME; \
	fi; \
	echo ""; \
	echo "$(GREEN)Testing with:$(NC)"; \
	echo "  GitLab URL: $$GITLAB_URL"; \
	echo "  Project ID: $$PROJECT_ID"; \
	echo "  MR IID: $$MR_IID"; \
	echo "  AI Provider: $$AI_MODEL"; \
	echo "  Model: $$MODEL_DISPLAY_NAME ($$MODEL_NAME)"; \
	echo ""; \
	python scripts/test_local.py --ai-model $$AI_MODEL --model-name $$MODEL_NAME

delete-comments: ## Delete all comments from an MR (for testing)
	@echo "$(BLUE)Delete MR Comments$(NC)"
	@echo ""
	@if [ -f .env ]; then \
		echo "$(GREEN)Loading environment from .env file...$(NC)"; \
		export $$(cat .env | grep -v '^#' | grep -v '^$$' | xargs); \
	fi; \
	if [ -z "$$GITLAB_TOKEN" ]; then \
		echo "$(RED)Error: GITLAB_TOKEN not set$(NC)"; \
		echo "Edit your .env file or run: export GITLAB_TOKEN=your-token"; \
		exit 1; \
	fi; \
	if [ -z "$$GITLAB_URL" ]; then \
		read -p "GitLab URL (default: https://gitlab.com): " gitlab_url; \
		export GITLAB_URL=$${gitlab_url:-https://gitlab.com}; \
	fi; \
	read -p "Project ID: " project_id; \
	read -p "MR IID: " mr_iid; \
	export PROJECT_ID=$$project_id; \
	export MR_IID=$$mr_iid; \
	echo ""; \
	echo "$(GREEN)Deleting comments from:$(NC)"; \
	echo "  GitLab URL: $$GITLAB_URL"; \
	echo "  Project ID: $$PROJECT_ID"; \
	echo "  MR IID: $$MR_IID"; \
	echo ""; \
	python ./scripts/delete_mr_comments.py

## Deployment targets

deploy: ## Deploy to cloud function (interactive)
	@echo "$(BLUE)Cloud Function Deployment$(NC)"
	@echo ""
	@echo "Select cloud provider:"
	@echo "  1) Google Cloud Functions (GCP)"
	@echo "  2) AWS Lambda"
	@echo "  3) DigitalOcean Functions"
	@echo ""
	@read -p "Enter choice [1-3]: " choice; \
	case $$choice in \
		1) $(MAKE) deploy-gcp ;; \
		2) $(MAKE) deploy-aws ;; \
		3) $(MAKE) deploy-digitalocean ;; \
		*) echo "$(RED)Invalid choice$(NC)"; exit 1 ;; \
	esac

deploy-gcp: ## Deploy to Google Cloud Functions
	@echo "$(BLUE)Deploying to Google Cloud Functions...$(NC)"
	@if [ -z "$$GOOGLE_API_KEY" ]; then \
		echo "$(RED)Error: GOOGLE_API_KEY not set$(NC)"; \
		exit 1; \
	fi
	@cd cloud_functions/gcp && ./deploy.sh
	@echo "$(GREEN)✓ Deployed to GCP$(NC)"

deploy-aws: ## Deploy to AWS Lambda
	@echo "$(BLUE)Deploying to AWS Lambda...$(NC)"
	@if [ -z "$$AWS_LAMBDA_ROLE_ARN" ]; then \
		echo "$(RED)Error: AWS_LAMBDA_ROLE_ARN not set$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$$GOOGLE_API_KEY" ]; then \
		echo "$(RED)Error: GOOGLE_API_KEY not set$(NC)"; \
		exit 1; \
	fi
	@cd cloud_functions/aws && ./deploy.sh
	@echo "$(GREEN)✓ Deployed to AWS$(NC)"

deploy-digitalocean: ## Deploy to DigitalOcean Functions
	@echo "$(BLUE)Deploying to DigitalOcean Functions...$(NC)"
	@if [ -z "$$GOOGLE_API_KEY" ]; then \
		echo "$(RED)Error: GOOGLE_API_KEY not set$(NC)"; \
		exit 1; \
	fi
	@cd cloud_functions/digitalocean && ./deploy.sh
	@echo "$(GREEN)✓ Deployed to DigitalOcean$(NC)"

## Utility targets

check-env: ## Check environment setup
	@echo "$(BLUE)Checking environment...$(NC)"
	@echo ""
	@if [ -f .env ]; then \
		echo "$(GREEN)Loading environment from .env file...$(NC)"; \
		echo ""; \
		export $$(cat .env | grep -v '^#' | grep -v '^$$' | xargs); \
	fi; \
	echo "$(YELLOW)API Keys:$(NC)"; \
	[ -n "$$GOOGLE_API_KEY" ] && echo "  $(GREEN)✓$(NC) GOOGLE_API_KEY" || echo "  $(RED)✗$(NC) GOOGLE_API_KEY"; \
	[ -n "$$ANTHROPIC_API_KEY" ] && echo "  $(GREEN)✓$(NC) ANTHROPIC_API_KEY" || echo "  $(YELLOW)○$(NC) ANTHROPIC_API_KEY (optional)"; \
	[ -n "$$OPENAI_API_KEY" ] && echo "  $(GREEN)✓$(NC) OPENAI_API_KEY" || echo "  $(YELLOW)○$(NC) OPENAI_API_KEY (optional)"; \
	echo ""; \
	echo "$(YELLOW)GitLab:$(NC)"; \
	[ -n "$$GITLAB_TOKEN" ] && echo "  $(GREEN)✓$(NC) GITLAB_TOKEN" || echo "  $(RED)✗$(NC) GITLAB_TOKEN"; \
	[ -n "$$GITLAB_URL" ] && echo "  $(GREEN)✓$(NC) GITLAB_URL: $$GITLAB_URL" || echo "  $(YELLOW)○$(NC) GITLAB_URL (will use default)"; \
	echo ""; \
	echo "$(YELLOW)Cloud CLIs:$(NC)"; \
	command -v gcloud >/dev/null 2>&1 && echo "  $(GREEN)✓$(NC) gcloud" || echo "  $(YELLOW)○$(NC) gcloud (for GCP deployment)"; \
	command -v aws >/dev/null 2>&1 && echo "  $(GREEN)✓$(NC) aws" || echo "  $(YELLOW)○$(NC) aws (for AWS deployment)"; \
	command -v doctl >/dev/null 2>&1 && echo "  $(GREEN)✓$(NC) doctl" || echo "  $(YELLOW)○$(NC) doctl (for DO deployment)"

load-env: ## Print export statements for .env/read.env (source with: source <(make load-env))
	@if [ ! -f .env ] && [ ! -f read.env ]; then \
		echo "$(RED)No .env or read.env file found$(NC)" >&2; \
		exit 1; \
	fi
	@echo "$(BLUE)Emitting environment exports$(NC)" >&2
	@python3 scripts/load_env.py

init: ## Initialize project (copy .env.example to .env)
	@if [ -f .env ]; then \
		echo "$(YELLOW).env already exists$(NC)"; \
	else \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env from .env.example$(NC)"; \
		echo "$(YELLOW)⚠ Edit .env and add your API keys$(NC)"; \
	fi

dev: install-dev init ## Quick start for development
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your API keys"
	@echo "  2. Run: make test-local"
	@echo "  3. Run: make deploy"