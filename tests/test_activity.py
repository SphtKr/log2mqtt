import pytest
import uuid
from src.log2mqtt.activity import Activity

def test_activity_initialization():
    config = {
        'name': 'Test Activity',
        'patterns': [{'method': 'GET'}],
        'timeout': 10
    }
    activity = Activity(config)
    
    assert activity.name == 'Test Activity'
    assert activity.timeout == 10
    assert len(activity.patterns) == 1
    assert isinstance(activity.id, uuid.UUID)

def test_activity_timeout_read_only():
    config = {'name': 'Test', 'timeout': 5}
    activity = Activity(config)
    
    with pytest.raises(AttributeError):
        activity.timeout = 10

def test_activity_id_read_only():
    config = {'name': 'Test'}
    activity = Activity(config)
    
    with pytest.raises(AttributeError):
        activity.id = uuid.uuid4()

def test_activity_matches_success():
    config = {
        'name': 'Test Activity',
        'patterns': [
            {'method': 'GET', 'hostname': 'example.com'},
            {'userAgent': '.*Bot.*'}
        ]
    }
    activity = Activity(config)
    
    # Matches first pattern
    assert activity.matches("https://example.com/path", "GET", "Mozilla/5.0") is not None
    # Matches second pattern
    assert activity.matches("https://other.com", "POST", "GoogleBot/2.1") is not None

def test_activity_matches_failure():
    config = {
        'name': 'Test Activity',
        'patterns': [
            {'method': 'GET', 'hostname': 'example.com'}
        ]
    }
    activity = Activity(config)
    
    # Wrong method
    assert activity.matches("https://example.com/path", "POST", "Mozilla/5.0") is None
    # Wrong hostname
    assert activity.matches("https://sample.com/path", "GET", "Mozilla/5.0") is None

def test_activity_no_patterns():
    config = {'name': 'Empty Activity', 'patterns': []}
    activity = Activity(config)
    
    assert activity.matches("https://example.com", "GET", "Mozilla/5.0") is None

def test_activity_empty_config():
    config = {}
    activity = Activity(config)
    
    assert activity.name is None
    assert activity.timeout == 0
    assert activity.matches("https://example.com", "GET", "Mozilla/5.0") is None