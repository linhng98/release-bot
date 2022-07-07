install:
	pip install -r requirements.txt

package:
	pip freeze > requirements.txt

format:
	autopep8 --in-place --recursive .