export VORTA_SRC := src/vorta
export FLATPAK_XML := src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
VERSION := $(shell python -c "from src.vorta._version import __version__; print(__version__)")

.PHONY : help
.DEFAULT_GOAL := help

clean:
	rm -rf dist/*

dist/Vorta.app: translations-to-qm clean
	pyinstaller --clean --noconfirm package/vorta.spec
	cp -R bin/darwin/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cp -R ${BORG_SRC}/dist/borg-dir dist/Vorta.app/Contents/Resources/
	rm -rf build/vorta
	rm -rf dist/vorta

borg:  ## Build Borg single-dir release for bundling in macOS
	rm -rf ${BORG_SRC}/dist/*
	cd ${BORG_SRC} && python setup.py clean && pip install -U -e .
	cd ${BORG_SRC} && pyinstaller --clean --noconfirm ../vorta/package/borg.spec .
	find ${BORG_SRC}/dist/borg-dir -type f \( -name \*.so -or -name \*.dylib -or -name borg.exe \) \
		-exec codesign --verbose --force --sign "${CERTIFICATE_NAME}" \
		--entitlements package/entitlements.plist --timestamp --deep --options runtime {} \;

dist/Vorta.dmg: dist/Vorta.app  ## Create notarized macOS DMG for distribution.
	sh package/macos-package-app.sh

github-release: dist/Vorta.dmg  ## Add new Github release and attach macOS DMG
	cp dist/Vorta.dmg dist/vorta-${VERSION}.dmg
	hub release create --attach=dist/vorta-${VERSION}.dmg v${VERSION}
	git checkout gh-pages
	git commit -m 'rebuild pages' --allow-empty
	git push upstream gh-pages
	git checkout master

pypi-release: translations-to-qm  ## Upload new release to PyPi
	python setup.py sdist
	twine upload dist/vorta-${VERSION}.tar.gz

bump-version:  ## Tag new version. First set new version number in src/vorta/_version.py
	xmlstarlet ed -L -u 'component/releases/release/@date' -v $(shell date +%F) ${FLATPAK_XML}
	xmlstarlet ed -L -u 'component/releases/release/@version' -v v${VERSION} ${FLATPAK_XML}
	git commit -a -m "Bump version to v${VERSION}"
	git tag -a v${VERSION}

translations-from-source:  ## Extract strings from source code / UI files, merge into .ts.
	pylupdate5 -verbose -translate-function trans_late \
			   ${VORTA_SRC}/*.py ${VORTA_SRC}/views/*.py ${VORTA_SRC}/borg/*.py \
			   ${VORTA_SRC}/assets/UI/*.ui \
			   -ts ${VORTA_SRC}/i18n/ts/vorta.en.ts

translations-push: translations-from-source  ## Upload .ts to Transifex.
	tx push -s

translations-pull:  ## Download .ts from Transifex.
	tx pull -a

translations-to-qm:  ## Compile .ts text files to binary .qm files.
	for f in $$(ls ${VORTA_SRC}/i18n/ts/vorta.*.ts); do lrelease $$f -qm ${VORTA_SRC}/i18n/qm/$$(basename $$f .ts).qm; done

flatpak-install: translations-to-qm
	pip3 install --prefix=/app --no-deps .
	install -D ${FLATPAK_XML} /app/share/metainfo/com.borgbase.Vorta.appdata.xml
	install -D package/icon.svg /app/share/icons/hicolor/scalable/apps/com.borgbase.Vorta.svg
	install -D package/icon-symbolic.svg /app/share/icons/hicolor/symbolic/apps/com.borgbase.Vorta-symbolic.svg
	install -D src/vorta/assets/metadata/com.borgbase.Vorta.desktop /app/share/applications/com.borgbase.Vorta.desktop

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
