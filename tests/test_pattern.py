import pytest
from src.log2mqtt.pattern import Pattern

def test_pattern_match_method_only():
    config = {'method': 'POST'}
    pattern = Pattern(config)
    assert pattern.matches("http://example.com", "POST", "Mozilla/5.0") is True
    assert pattern.matches("http://example.com", "GET", "Mozilla/5.0") is False

def test_pattern_match_url_regex():
    config = {'url': r'.*\.google\.com/.*'}
    pattern = Pattern(config)
    assert pattern.matches("https://www.google.com/search?q=test", "GET", "Mozilla/5.0") is True
    assert pattern.matches("https://example.com/search?q=test", "GET", "Mozilla/5.0") is False

def test_pattern_match_hostname_substring():
    config = {'hostname': 'github'}
    pattern = Pattern(config)
    assert pattern.matches("https://github.com/user/repo", "GET", "Mozilla/5.0") is True
    assert pattern.matches("https://google.com", "GET", "Mozilla/5.0") is False

def test_pattern_match_useragent_regex():
    config = {'userAgent': r'.*Bot.*'}
    pattern = Pattern(config)
    assert pattern.matches("http://example.com", "GET", "GoogleBot/2.1") is True
    assert pattern.matches("http://example.com", "GET", "Mozilla/5.0") is False

def test_pattern_match_multiple_criteria_success():
    # All criteria must match
    config = {
        'method': 'GET',
        'hostname': 'wikipedia',
        'url': r'.*/wiki/.*'
    }
    pattern = Pattern(config)
    assert pattern.matches("https://en.wikipedia.org/wiki/Python", "GET", "Mozilla/5.0") is True

def test_pattern_match_multiple_criteria_failure():
    # One criterion fails
    config = {
        'method': 'GET',
        'hostname': 'wikipedia',
  	'url': r'.*/wiki/.*'
    }
    pattern = Pattern(config)
    # Method is wrong
    assert pattern.matches("https://en.wikipedia.org/wiki/Python", "POST", "Mozilla/5.0") is False
    # Hostname is wrong
    assert pattern.matches("https://google.com/wiki/Python", "GET", "Mozilla/5.0") is False
    # URL regex is wrong
    assert pattern.matches("https://en.wikipedia.org/main_page", "GET", "Mozilla/5.0") is False

def test_pattern_match_invalid_url_fallback():
    # Test fallback logic when URL is not a valid URL
    config = {'hostname': 'example'}
    pattern = Pattern(config)
    # Should search in raw string if urlparse fails or doesn't find hostname
    assert pattern.matches("just_a_string_with_example_in_it", "GET", "Mozilla/5.0") is True

def test_pattern_empty_config():
    # An empty config should match everything (it has no restrictions)
    config = {}
    pattern = Pattern(config)
    assert pattern.matches("http://anything.com", "ANY", "ANY_UA") is True