# Retrieval Evaluation Rubric

For each query:

PASS if:
- The expected_primary_doc appears in Top-3 results
- The top-ranked document matches expected_doc_type

WARN if:
- Expected doc appears in Top-5 but not Top-3
- Correct info present but wrong doc_type ranked first

FAIL if:
- Expected document not present in Top-5
- Deprecated or unrelated document ranked above expected
