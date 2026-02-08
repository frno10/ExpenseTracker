"""
Unit tests for configuration management.
"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings, DatabaseConfig


class TestDatabaseConfig:
    """Test database configuration parsing."""
    
    def test_valid_database_url_parsing(self):
        """Test parsing of valid database URL."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        config = DatabaseConfig(url)
        
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "testdb"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.max_retries == 5
        assert config.retry_delay == 1.0
        assert config.connection_timeout == 30
    
    def test_database_url_with_default_port(self):
        """Test database URL without explicit port."""
        url = "postgresql://user:pass@localhost/testdb"
        config = DatabaseConfig(url)
        
        assert config.host == "localhost"
        assert config.port == 5432  # Default PostgreSQL port
        assert config.database == "testdb"
    
    def test_render_database_url_format(self):
        """Test Render-style database URL."""
        url = "postgresql://user:pass@host.render.com:5432/dbname"
        config = DatabaseConfig(url)
        
        assert config.host == "host.render.com"
        assert config.port == 5432
        assert config.database == "dbname"


class TestSettings:
    """Test application settings validation."""
    
    def test_valid_database_url_validation(self):
        """Test validation of valid database URL."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'}):
            settings = Settings()
            assert settings.database_url == 'postgresql://user:pass@localhost:5432/testdb'
    
    def test_invalid_database_url_no_scheme(self):
        """Test validation fails for URL without proper scheme."""
        with patch.dict(os.environ, {'DATABASE_URL': '//localhost:5432/testdb'}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must include a scheme" in str(exc_info.value)
    
    def test_invalid_database_url_no_hostname(self):
        """Test validation fails for URL without hostname."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql:///testdb'}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must include a hostname" in str(exc_info.value)
    
    def test_invalid_database_url_no_database(self):
        """Test validation fails for URL without database name."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost:5432/'}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must include a database name" in str(exc_info.value)
    
    def test_empty_database_url(self):
        """Test validation fails for empty database URL."""
        with patch.dict(os.environ, {'DATABASE_URL': ''}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "DATABASE_URL is required" in str(exc_info.value)
    
    def test_get_database_config(self):
        """Test getting parsed database configuration."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'}):
            settings = Settings()
            db_config = settings.get_database_config()
            
            assert isinstance(db_config, DatabaseConfig)
            assert db_config.host == "localhost"
            assert db_config.database == "testdb"
    
    @patch.dict(os.environ, {'RENDER': 'true', 'RENDER_SERVICE_NAME': 'test-service'})
    def test_render_environment_detection(self):
        """Test detection of Render environment."""
        settings = Settings()
        assert settings.is_render_environment() is True
        
        render_config = settings.get_render_config()
        assert render_config['is_render'] is True
        assert render_config['render_service_name'] == 'test-service'
    
    def test_local_environment_detection(self):
        """Test detection of local development environment."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.is_render_environment() is False
            
            render_config = settings.get_render_config()
            assert render_config['is_render'] is False
            assert render_config['render_service_name'] is None
    
    @patch('app.core.config.logger')
    def test_log_config_summary_local(self, mock_logger):
        """Test configuration logging for local environment."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost:5432/testdb'}):
            settings = Settings()
            settings.log_config_summary()
            
            # Verify logging calls were made
            assert mock_logger.info.called
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            
            assert any("Application Configuration" in call for call in log_calls)
            assert any("Database Host: localhost:5432" in call for call in log_calls)
            assert any("Local Development Environment" in call for call in log_calls)
    
    @patch('app.core.config.logger')
    @patch.dict(os.environ, {'RENDER': 'true', 'RENDER_SERVICE_NAME': 'test-service'})
    def test_log_config_summary_render(self, mock_logger):
        """Test configuration logging for Render environment."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@host.render.com:5432/testdb'}):
            settings = Settings()
            settings.log_config_summary()
            
            # Verify logging calls were made
            assert mock_logger.info.called
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            
            assert any("Render Environment Detected" in call for call in log_calls)
            assert any("Service Name: test-service" in call for call in log_calls)