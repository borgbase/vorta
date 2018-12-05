
Vorta.app:
	#pyrcc5 -o src/vorta/views/collection_rc.py src/vorta/assets/icons/collection.qrc
	pyinstaller --clean --noconfirm vorta.spec
	cp -R bin/macosx64/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cd dist; codesign --deep --sign 'Developer ID Application: Manuel Riel (CNMSCAXT48)' Vorta.app

Vorta.dmg: Vorta.app
	# sleep 2; cd dist; zip -9rq vorta-0.5.3.zip Vorta.app
	rm -rf dist/vorta-0.5.3.dmg
	sleep 2; appdmg appdmg.json dist/vorta-0.5.3.dmg

github-release: Vorta.dmg
	hub release create --prerelease --attach=dist/vorta-0.5.3.dmg v0.5.3
	git checkout gh-pages
	git commit -m 'rebuild pages' --allow-empty
	git push upstream gh-pages
	git checkout master

pypi-release:
	python setup.py sdist
	twine upload dist/vorta-0.5.3.tar.gz

bump-version:
	git log $$(git describe --tags --abbrev=0)..HEAD --pretty=format:"- %s"
	bumpversion patch
#	bumpversion minor
	git push
	git push --tags

travis-debug:
	  curl -s -X POST \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -H "Travis-API-Version: 3" \
       -H "Authorization: token ${TRAVIS_TOKEN}" \
       -d '{ "quiet": true }' \
       https://api.travis-ci.org/job/${TRAVIS_JOB_ID}/debug
