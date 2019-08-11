export VORTA_SRC := src/vorta
export QT_SELECT=5

.PHONY : help
.DEFAULT_GOAL := help
DATE = "$(shell date +%F)"

icon-resources:  ## Compile SVG icons to importable resource files.
	pyrcc5 -o src/vorta/views/dark/collection_rc.py src/vorta/assets/icons/dark/collection.qrc
	pyrcc5 -o src/vorta/views/light/collection_rc.py src/vorta/assets/icons/light/collection.qrc

Vorta.app: translations-to-qm
	pyinstaller --clean --noconfirm vorta.spec
	cp -R bin/darwin/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cd dist; codesign --deep --sign 'Developer ID Application: Manuel Riel (CNMSCAXT48)' Vorta.app

Vorta.dmg-Vagrant:
	vagrant up darwin64
	rm -rf dist/*
	vagrant scp darwin64:/vagrant/dist/Vorta.app dist/
	vagrant halt darwin64
	cp -R bin/darwin/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cd dist; codesign --deep --sign 'Developer ID Application: Manuel Riel (CNMSCAXT48)' Vorta.app
	sleep 2; appdmg appdmg.json dist/vorta-0.6.22.dmg

Vorta.dmg: Vorta.app
	rm -rf dist/vorta-0.6.22.dmg
	sleep 2; appdmg appdmg.json dist/vorta-0.6.22.dmg

github-release: Vorta.dmg
	hub release create --attach=dist/vorta-0.6.22.dmg v0.6.22
	git checkout gh-pages
	git commit -m 'rebuild pages' --allow-empty
	git push upstream gh-pages
	git checkout master

pypi-release: translations-to-qm
	python setup.py sdist
	twine upload dist/vorta-0.6.22.tar.gz

bump-version:  ## Add new version tag and push to upstream repo.
	bumpversion patch
	#bumpversion minor
	xmlstarlet ed -L -u 'component/releases/release/@date' -v $$(date +%F) src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml
	git commit -a -m 'Bump version'
	git push upstream

travis-debug:  ## Prepare connecting to Travis instance via SSH.
	  curl -s -X POST \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -H "Travis-API-Version: 3" \
       -H "Authorization: token ${TRAVIS_TOKEN}" \
       -d '{ "quiet": true }' \
       https://api.travis-ci.org/job/${TRAVIS_JOB_ID}/debug

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
	mkdir -p /app/share/metainfo/
	cp src/vorta/assets/metadata/com.borgbase.Vorta.appdata.xml /app/share/metainfo/
	mkdir -p /app/share/icons/hicolor/512x512/apps/
	cp src/vorta/assets/icons/512x512/com.borgbase.Vorta.png /app/share/icons/hicolor/512x512/apps/
	mkdir -p /app/share/icons/hicolor/256x256/apps/
	cp src/vorta/assets/icons/256x256/com.borgbase.Vorta.png /app/share/icons/hicolor/256x256/apps/
	mkdir -p /app/share/icons/hicolor/128x128/apps/
	cp src/vorta/assets/icons/128x128/com.borgbase.Vorta.png /app/share/icons/hicolor/128x128/apps/
	mkdir -p /app/share/icons/hicolor/64x64/apps/
	cp src/vorta/assets/icons/64x64/com.borgbase.Vorta.png /app/share/icons/hicolor/64x64/apps/
	mkdir -p /app/share/icons/hicolor/48x48/apps/
	cp src/vorta/assets/icons/48x48/com.borgbase.Vorta.png /app/share/icons/hicolor/48x48/apps/
	mkdir -p /app/share/icons/hicolor/32x32/apps/
	cp src/vorta/assets/icons/32x32/com.borgbase.Vorta.png /app/share/icons/hicolor/32x32/apps/
	mkdir -p /app/share/icons/hicolor/24x24/apps/
	cp src/vorta/assets/icons/24x24/com.borgbase.Vorta.png /app/share/icons/hicolor/24x24/apps/
	mkdir -p /app/share/applications/
	cp src/vorta/assets/metadata/com.borgbase.Vorta.desktop /app/share/applications/

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
