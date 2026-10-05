.PHONY: check-clean version-patch version-minor version-major

# Target name minus the prefix.
BUMP = $(@:version-%=%)

check-clean:
	@test -z "$$(git status --porcelain)" || { echo "Git tree is dirty."; exit 1; }

version-patch version-minor version-major: check-clean
	@NEW_VERSION=$$(uv version --bump $(BUMP) --short) && \
	git add pyproject.toml uv.lock && \
	git commit -q -m "vexicon v$$NEW_VERSION"
