"""
Tests for configuration module
"""
import os
import pytest
from unittest.mock import patch


def test_auto_open_run_default():
    """Test AUTO_OPEN_RUN default value"""
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import config
        importlib.reload(config)
        # Default should be True
        assert config.AUTO_OPEN_RUN is True


def test_auto_open_run_from_env():
    """Test AUTO_OPEN_RUN from environment variable"""
    with patch.dict(os.environ, {"AUTO_OPEN_RUN": "false"}, clear=False):
        import importlib
        import config
        importlib.reload(config)
        assert config.AUTO_OPEN_RUN is False


def test_branch_filter_patterns_default():
    """Test BRANCH_FILTER_PATTERNS default values"""
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import config
        importlib.reload(config)
        assert len(config.BRANCH_FILTER_PATTERNS) > 0
        assert "^main$" in config.BRANCH_FILTER_PATTERNS


def test_branch_filter_patterns_from_env():
    """Test BRANCH_FILTER_PATTERNS from environment variable"""
    with patch.dict(os.environ, {"BRANCH_FILTER_PATTERNS": "^main$,^develop$"}, clear=False):
        import importlib
        import config
        importlib.reload(config)
        assert "^main$" in config.BRANCH_FILTER_PATTERNS
        assert "^develop$" in config.BRANCH_FILTER_PATTERNS


def test_check_permissions_default():
    """Test CHECK_PERMISSIONS default value"""
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import config
        importlib.reload(config)
        assert config.CHECK_PERMISSIONS is True


def test_check_permissions_from_env():
    """Test CHECK_PERMISSIONS from environment variable"""
    with patch.dict(os.environ, {"CHECK_PERMISSIONS": "false"}, clear=False):
        import importlib
        import config
        importlib.reload(config)
        assert config.CHECK_PERMISSIONS is False


def test_use_user_token_for_workflows_default():
    """Test USE_USER_TOKEN_FOR_WORKFLOWS default value"""
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import config
        importlib.reload(config)
        assert config.USE_USER_TOKEN_FOR_WORKFLOWS is True


def test_use_user_token_for_workflows_from_env():
    """Test USE_USER_TOKEN_FOR_WORKFLOWS from environment variable"""
    with patch.dict(os.environ, {"USE_USER_TOKEN_FOR_WORKFLOWS": "false"}, clear=False):
        import importlib
        import config
        importlib.reload(config)
        assert config.USE_USER_TOKEN_FOR_WORKFLOWS is False

