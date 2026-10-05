.PHONY: help check-clean version-patch version-minor version-major publish
.DEFAULT_GOAL := help

help:
	@echo "Targets: check-clean version-patch version-minor version-major publish"

# Target name minus the prefix.
BUMP = $(@:version-%=%)

check-clean:
	@test -z "$$(git status --porcelain)" || { echo "Git tree is dirty."; exit 1; }

version-patch version-minor version-major: check-clean
	@NEW_VERSION=$$(uv version --bump $(BUMP) --short) && \
	git add pyproject.toml uv.lock && \
	git commit -q -m "vexicon v$$NEW_VERSION"

# The PyPI token is read from keyring under service PYPI, username PUBLISH_TOKEN.
publish: check-clean
	uv run pytest -q
	uv build --clear --no-sources
	UV_PUBLISH_TOKEN="$$(uvx keyring get PYPI PUBLISH_TOKEN)" uv publish
