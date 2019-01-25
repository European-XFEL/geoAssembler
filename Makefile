# makefile used for testing

install:
	python3 -m pip install -U -e .[test]

test:
	python3 -m pytest -v

