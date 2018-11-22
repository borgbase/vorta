
Vorta.app:
	#pyrcc5 -o src/vorta/views/collection_rc.py src/vorta/assets/icons/collection.qrc
	pyinstaller --clean --noconfirm vorta.spec
	cp -R bin/macosx64/Sparkle.framework dist/Vorta.app/Contents/Frameworks/
	cd dist; codesign --deep --sign 'Developer ID Application: Manuel Riel (CNMSCAXT48)' Vorta.app

Vorta.dmg: Vorta.app
	# sleep 2; cd dist; zip -9rq vorta-0.4.6.zip Vorta.app
	rm -rf dist/vorta-0.4.6.dmg
	sleep 2; appdmg appdmg.json dist/vorta-0.4.6.dmg

github-release: Vorta.dmg
	hub release create --prerelease --attach=dist/vorta-0.4.6.dmg v0.4.6
	git checkout gh-pages
	git commit -m 'rebuild pages' --allow-empty
	git push origin gh-pages
	git checkout master

pypi-release:
	python setup.py sdist
	twine upload dist/vorta-0.4.6.tar.gz

bump-version:
	bumpversion patch
#	bumpversion minor
	git push
	git push --tags
	git log $(git describe --tags --abbrev=0)..HEAD --pretty=format:"- %s"

travis-debug:
	  curl -s -X POST \
       -H "Content-Type: application/json" \
       -H "Accept: application/json" \
       -H "Travis-API-Version: 3" \
       -H "Authorization: token ${TRAVIS_TOKEN}" \
       -d '{ "quiet": true }' \
       https://api.travis-ci.org/job/${TRAVIS_JOB_ID}/debug
