import sys
import traceback
import pytest
from unittest.mock import patch
import sqlalchemy

original_create_engine = sqlalchemy.create_engine

def mock_create_engine(*args, **kwargs):
    if 'pool_size' in kwargs or (len(args) > 0 and 'sqlite' in str(args[0])):
        print("===================== CREATE_ENGINE CALLED =====================")
        print("ARGS:", args)
        print("KWARGS:", kwargs)
        traceback.print_stack()
        print("================================================================")
    return original_create_engine(*args, **kwargs)

with patch('sqlalchemy.create_engine', side_effect=mock_create_engine):
    pytest.main(["tests/test_api.py::test_health_endpoint", "-s"])
