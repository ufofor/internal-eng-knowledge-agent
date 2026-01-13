# =========================================
# Internal Engineering Knowledge Agent
# Makefile
# =========================================

PYTHON := .venv/bin/python

.PHONY: help corpus validate all clean

help:
	@echo ""
	@echo "Available commands:"
	@echo "  make corpus    -> generate starter knowledge corpus"
	@echo "  make validate  -> validate corpus metadata"
	@echo "  make all       -> run corpus + validation"
	@echo "  make clean     -> remove generated artifacts (safe)"
	@echo ""

corpus:
	@echo "📄 Generating knowledge corpus..."
	$(PYTHON) scripts/make_corpus.py

validate:
	@echo "🔍 Validating corpus metadata..."
	$(PYTHON) scripts/validate_metadata.py

all: corpus validate
	@echo "✅ Corpus generation + validation complete."

clean:
	@echo "🧹 Nothing to clean yet (placeholder)"
index:
	@echo "🧠 Building FAISS vector index..."
	$(PYTHON) scripts/build_index.py
query:
	@echo "🔎 Querying FAISS index..."
	$(PYTHON) scripts/query_index.py "$(Q)" $(K)
query_policy:
	@echo "🔎 Querying with policy rerank + dedup + quotas..."
	$(PYTHON) scripts/query_index_policy.py "$(Q)" $(K) $(C)
eval:
	@echo "🧪 Running retrieval evaluation..."
	$(PYTHON) scripts/run_eval.py