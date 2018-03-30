VERSION_PART ?= patch

.PHONY: clean
clean:
	@rm -rf build dist ddtrace_graphql.egg-info

.PHONY: test
test:
	@pip install --editable .[test]
	@tox

.PHONY: versionbump
versionbump:
	bumpversion  \
		--commit \
		--current-version `cat VERSION`  \
		$(VERSION_PART) ./VERSION

.PHONY: build
build: clean
	python setup.py sdist bdist_wheel

.PHONY: testpublish
testpublish: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*


.PHONY: publish
publish: build
	twine upload dist/*
