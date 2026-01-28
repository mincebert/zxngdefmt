all: zxngdefmt

.PHONY: remake zxngdefmt upload clean


remake: clean all

zxngdefmt:
	./setup.py sdist bdist_wheel

upload:
	python3 -m twine upload dist/*

clean:
	rm -rf build dist zxngdefmt.egg-info
