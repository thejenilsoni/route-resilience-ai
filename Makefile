.PHONY: api web test quality demo train

api:
	PYTHONPATH=ml:. uvicorn services.api.app.main:app --reload --port 8000

web:
	npm run dev

test:
	PYTHONPATH=ml:. pytest
	node --test apps/web/tests/*.test.mjs

quality:
	ruff check ml services tests scripts
	PYTHONPATH=ml:. pytest
	node --test apps/web/tests/*.test.mjs
	npm run typecheck
	npm run build

demo:
	PYTHONPATH=ml python scripts/generate_demo_data.py

train:
	PYTHONPATH=ml python scripts/train_baseline.py
