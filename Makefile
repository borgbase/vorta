export VORTA_SRC := src/vorta
export CERTIFICATE_NAME := "Developer ID Application: Manuel Riel (CNMSCAXT48)"

.PHONY : help
.DEFAULT_GOAL := help
DATE = "$(shell date +%F)"

clean:
	rm -rf dist/*

dist/Vorta.app: translations-to-qm clean
	pyinstaller --clean --noconfirm package/vorta.spec
	cp -R bin/darwin/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cp -R ../borg/dist/borg-dir dist/Vorta.app/Contents/Resources/
	rm -rf build/vorta
	rm -rf dist/vorta

borg:
	cd ../borg && pyinstaller --clean --noconfirm ../vorta/package/borg.spec .
	find ../borg/dist/borg-dir -type f \( -name \*.so -or -name \*.dylib -or -name borg.exe \) \
		-exec codesign --verbose --force --sign $(CERTIFICATE_NAME) \
		--entitlements package/entitlements.plist --timestamp --deep --options runtime {} \;

dist/Vorta.dmg: dist/Vorta.app
	sh package/macos-package-app.sh

github-release: dist/Vorta.dmg
	cp dist/Vorta.dmg dist/vorta-0.7.0.dmg
	hub release create --attach=dist/vorta-0.7.0.dmg v0.7.0
	git checkout gh-pages
	git commit -m 'rebuild pages' --allow-empty
	git push upstream gh-pages
	git checkout master

pypi-release: translations-to-qm
	python setup.py sdist
	twine upload dist/vorta-0.7.0.tar.gz

bump-version:  ## Add new version tag and push to upstream repo.
	bumpversion patch
	#bumpversion minor
	xmlstarlet ed -L -u 'component/releases/release/@date' -v $$(date +%F) src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
	git commit -a -m 'Bump version'
	git push upstream

translations-from-source:  ## Extract strings from source code / UI files, merge into .ts.
	pylupdate5 -verbose -translate-function trans_late \
			   $$VORTA_SRC/*.py $$VORTA_SRC/views/*.py $$VORTA_SRC/borg/*.py \
			   $$VORTA_SRC/assets/UI/*.ui \
			   -ts $$VORTA_SRC/i18n/ts/vorta.en_US.ts

translations-push: translations-from-source  ## Upload .ts to Transifex.
	tx push -s

translations-pull:  ## Download .ts from Transifex.
	tx pull -a

translations-to-qm:  ## Compile .ts text files to binary .qm files.
	for f in $$(ls $$VORTA_SRC/i18n/ts/vorta.*.ts); do lrelease $$f -qm $$VORTA_SRC/i18n/qm/$$(basename $$f .ts).qm; done

flatpak-install: translations-to-qm
	pip3 install --prefix=/app --no-deps .
	install -D src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml /app/share/metainfo/com.borgbase.Vorta.appdata.xml
	install -D package/icon.svg /app/share/icons/hicolor/scalable/apps/com.borgbase.Vorta.svg
	install -D package/icon-symbolic.svg /app/share/icons/hicolor/symbolic/apps/com.borgbase.Vorta-symbolic.svg
	install -D src/vorta/assets/metadata/com.borgbase.Vorta.desktop /app/share/applications/com.borgbase.Vorta.desktop

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
