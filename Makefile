.PHONY: check-clean version-patch version-minor version-major publish

# Target name minus the prefix.
BUMP = $(@:version-%=%)

check-clean:
	@test -z "$$(git status --porcelain)" || { echo "Git tree is dirty."; exit 1; }

version-patch version-minor version-major: check-clean
	@NEW_VERSION=$$(uv version --bump $(BUMP) --short) && \
	git add pyproject.toml uv.lock && \
	git commit -q -m "vexicon v$$NEW_VERSION"

# uv publish reads the PyPI token from UV_PUBLISH_TOKEN.
publish: check-clean
	uv run pytest -q
	uv build --clear --no-sources
	uv publish
