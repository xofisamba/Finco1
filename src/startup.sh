#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
streamlit run src/app.py --server.port=8502 --server.address=0.0.0.0 "$@"