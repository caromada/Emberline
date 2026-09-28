.PHONY: test demo dev build validate data

test:
	cd pipeline && ../.venv/bin/pytest -q

demo:
	.venv/bin/python pipeline/scripts/make_demo_csv.py
	rm -rf data
	cd pipeline && ../.venv/bin/python -m emberline.run \
		--input-csv scripts/demo_firms.csv --backfill \
		--data-dir ../data --static-window-days 8

validate:
	.venv/bin/python pipeline/scripts/validate_nifc.py --data-dir data

dev:
	cd web && npm run dev

build:
	cd web && npm run build

# fetch the live dataset CI publishes to the `data` branch
data:
	rm -rf data
	git clone --quiet --depth 1 --branch data https://github.com/caromada/Emberline.git data
