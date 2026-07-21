import sys
import pytest
from unittest.mock import patch
import sqlalchemy

original_create_engine = sqlalchemy.create_engine

def mock_create_engine(*args, **kwargs):
    print("=========================================")
    print("CREATE ENGINE CALLED WITH:")
    print("ARGS:", args)
    print("KWARGS:", kwargs)
    print("=========================================")
    return original_create_engine(*args, **kwargs)

with patch('sqlalchemy.create_engine', side_effect=mock_create_engine):
    pytest.main(["tests/test_api.py::test_health_endpoint", "-s"])
