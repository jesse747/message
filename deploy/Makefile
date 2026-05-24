.PHONY: help deploy-image deploy-run deploy-stop deploy-logs

HOST ?= root@your-vps-ip

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

deploy-image: ## Build LXC container image (placeholder)
	@echo "Use 'lxc-create' manually or via setup-container.sh inside the container."
	@echo "See deploy/lxc/setup-container.sh for the bootstrap script."

deploy-run: ## Copy code + run setup-container.sh on remote host
	rsync -a --exclude venv --exclude __pycache__ --exclude .git \
		../ $(HOST):/opt/message-build/
	ssh $(HOST) "bash /opt/message-build/deploy/lxc/setup-container.sh"

deploy-logs: ## Tail the gunicorn access log over SSH
	ssh $(HOST) "tail -f /var/log/message/access.log"

deploy-status: ## Check service status on remote host
	ssh $(HOST) "systemctl status message --no-pager && echo '---' && nginx -t"

deploy-restart: ## Restart the API service on remote host
	ssh $(HOST) "systemctl restart message"

rsync-skip-deploy: ## Quick code sync without re-running setup (dev iteration)
	rsync -a --delete --exclude venv --exclude __pycache__ --exclude .git \
		--exclude '*.db' --exclude .env \
		../ $(HOST):/opt/message/
	ssh $(HOST) "cd /opt/message && venv/bin/pip install -e . && systemctl restart message"
