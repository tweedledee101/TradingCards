#!/usr/bin/env python3
import ast, sys
with open("backend/utils/collectors_edge_result.py") as f:
    source = f.read()
try:
    ast.parse(source)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)

# Now try actual import
try:
    from backend.utils.collectors_edge_result import (
        call_ce_identify_api,
        ce_extracted_from_api_json,
        analyze_ce_for_pipeline,
    )
    print("Import OK")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
