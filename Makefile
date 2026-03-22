all: zxngdefmt

.PHONY: remake zxngdefmt upload clean


remake: clean all

zxngdefmt:
	python3 -m build

upload:
	python3 -m twine upload dist/*

clean:
	rm -rf build dist zxngdefmt.egg-info
