# makefile used for testing

DEPLOY_PATH=/gpfs/exfel/sw/software/geoAssembler
ENV_PATH=$(DEPLOY_PATH)/env

deploy:
	echo $(ENV_PATH)
	rm -fr $(DEPLOY_PATH)
	mkdir -p $(DEPLOY_PATH)
	conda create -y -p $(ENV_PATH) python=3.6 h5py matplotlib future
	$(ENV_PATH)/bin/python -m pip install .
	ln $(DEPLOY_PATH)/env/bin/geoAssemblerGui $(DEPLOY_PATH)/geoAssemblerGui

install:
	python3 -m pip install -U -e .[test]

test:
	python3 -m pytest -v
