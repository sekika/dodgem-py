import pytest
import json
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dodgem.dodgem import Dodgem

@pytest.fixture
def mock_gzip_json():
    with patch("gzip.open") as mock_file:
        with patch("json.load") as mock_json_load:
            mock_json_load.return_value = {'3': {}, '4': {}, '5': {}}
            yield mock_json_load

@pytest.fixture
def mock_mongo():
    with patch("pymongo.MongoClient") as mock_client:
        yield mock_client

@pytest.fixture
def game(mock_gzip_json, mock_mongo):
    engine = Dodgem(n=3, evalmap="dummy_path.gz")
    # FIX: Initialize use_mongo explicitly since tests skip set_level()
    engine.use_mongo = False 
    return engine
