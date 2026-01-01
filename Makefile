export VORTA_SRC := src/vorta
export APPSTREAM_METADATA := src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
VERSION := $(shell uv run python -c "from src.vorta._version import __version__; print(__version__)")

.PHONY: help clean lint test test-unit test-integration \
        bump-version pypi-release release-preflight changelog update-appcast \
        translations-from-source translations-push translations-pull translations-to-qm translations-update \
        flatpak-install
.DEFAULT_GOAL := help

# Set Homebrew location to /opt/homebrew on Apple Silicon, /usr/local on Intel
ifeq ($(shell uname -m),arm64)
	export HOMEBREW = /opt/homebrew
else
	export HOMEBREW = /usr/local
endif

clean:
	rm -rf dist/*

dist/Vorta.app:  ## Build macOS app locally (without Borg)
	uv run pyinstaller --clean --noconfirm package/vorta.spec
	cp -R ${HOMEBREW}/Caskroom/sparkle/*/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	rm -rf build/vorta dist/vorta

dist/Vorta.dmg: dist/Vorta.app  ## Create notarized macOS DMG for distribution.
	python3 package/fix_app_qt_folder_names_for_codesign.py dist/Vorta.app
	cd dist && sh ../package/macos-package-app.sh

pypi-release: translations-to-qm  ## Upload new release to PyPi
	uv run python -m build --sdist
	uv run twine upload dist/vorta-${VERSION}.tar.gz

release-preflight:  ## Check release prerequisites
	@echo "Checking release prerequisites..."
	@git diff --quiet || (echo "Error: Uncommitted changes" && exit 1)
	@git diff --cached --quiet || (echo "Error: Staged changes" && exit 1)
	@test "$$(git branch --show-current)" = "master" || (echo "Error: Not on master branch" && exit 1)
	@echo "Version: ${VERSION}"
	@echo "All checks passed"

bump-version: release-preflight  ## Tag new version. First set new version number in src/vorta/_version.py
	xmlstarlet ed -L -u 'component/releases/release/@date' -v $(shell date +%F) ${APPSTREAM_METADATA}
	xmlstarlet ed -L -u 'component/releases/release/@version' -v v${VERSION} ${APPSTREAM_METADATA}
	git commit -a -m "Bump version to v${VERSION}"
	git tag -a v${VERSION} -m "Release v${VERSION}"

translations-from-source:  ## Extract strings from source code / UI files, merge into .ts.
	pylupdate5 -verbose -translate-function trans_late \
			   $$(find ${VORTA_SRC} -iname "*.py" -o -iname "*.ui") \
			   -ts ${VORTA_SRC}/i18n/ts/vorta.en.ts

translations-push: translations-from-source  ## Upload .ts to Transifex.
	tx push -s

translations-pull:  ## Download .ts from Transifex.
	tx pull -a

translations-to-qm:  ## Compile .ts text files to binary .qm files.
	for f in $$(ls ${VORTA_SRC}/i18n/ts/vorta.*.ts); do lrelease $$f -qm ${VORTA_SRC}/i18n/qm/$$(basename $$f .ts).qm; done

translations-update: translations-pull translations-to-qm  ## Pull translations and compile to .qm

changelog:  ## Show commits since last tag
	@PREV_TAG=$$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo ""); \
	if [ -n "$$PREV_TAG" ]; then \
		echo "Changes since $$PREV_TAG:"; \
		git log --oneline $$PREV_TAG..HEAD; \
	else \
		echo "No previous tag found"; \
		git log --oneline -20; \
	fi

update-appcast:  ## Update Sparkle appcast on gh-pages branch
	git stash --include-untracked || true
	git checkout gh-pages
	uv run python generate_appcast.py --include-prereleases appcast-pre.xml
	uv run python generate_appcast.py appcast.xml
	git add appcast.xml appcast-pre.xml
	git commit -m "Update appcast for v${VERSION}"
	git push upstream gh-pages
	git checkout master
	git stash pop || true

flatpak-install: translations-to-qm
	pip3 install --verbose --exists-action=i --no-index --find-links=\"file://${PWD}\" --prefix=${FLATPAK_DEST} --no-build-isolation .
	install -D ${APPSTREAM_METADATA} ${FLATPAK_DEST}/share/metainfo/com.borgbase.Vorta.appdata.xml
	install -D src/vorta/assets/icons/icon.svg ${FLATPAK_DEST}/share/icons/hicolor/scalable/apps/com.borgbase.Vorta.svg
	install -D package/icon-symbolic.svg ${FLATPAK_DEST}/share/icons/hicolor/symbolic/apps/com.borgbase.Vorta-symbolic.svg
	install -D src/vorta/assets/metadata/com.borgbase.Vorta.desktop ${FLATPAK_DEST}/share/applications/com.borgbase.Vorta.desktop

lint:
	uv run pre-commit run --all-files --show-diff-on-failure

test:
	uv run nox -- --cov=vorta

test-unit:
	uv run nox -- --cov=vorta tests/unit

test-integration:
	uv run nox -- --cov=vorta tests/integration

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
