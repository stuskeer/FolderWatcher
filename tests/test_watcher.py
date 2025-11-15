"""Tests for watcher module"""
import os
import tempfile
import shutil
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from watcher import NewFileHandler, ensure_dir, setup_logger, parse_args


class TestEnsureDir:
    """Test suite for ensure_dir function"""

    def test_ensure_dir_creates_directory(self):
        """Test that ensure_dir creates a directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "test_dir")
            assert not os.path.exists(new_dir)
            
            ensure_dir(new_dir)
            
            assert os.path.exists(new_dir)
            assert os.path.isdir(new_dir)

    def test_ensure_dir_existing_directory(self):
        """Test that ensure_dir handles existing directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise exception
            ensure_dir(tmpdir)
            assert os.path.exists(tmpdir)

    def test_ensure_dir_nested_paths(self):
        """Test that ensure_dir creates nested directory structures"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            ensure_dir(nested)
            assert os.path.exists(nested)


class TestSetupLogger:
    """Test suite for setup_logger function"""

    def test_setup_logger_creates_file(self):
        """Test that setup_logger creates a log file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = os.path.join(tmpdir, "test.log")
            logger = setup_logger(logfile)
            
            logger.info("Test message")
            
            assert os.path.exists(logfile)
            assert logger.name == "folder_watcher"
            
            # Cleanup: remove handlers to release file locks
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    def test_setup_logger_returns_logger(self):
        """Test that setup_logger returns a Logger instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = os.path.join(tmpdir, "test.log")
            logger = setup_logger(logfile)
            
            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.INFO
            
            # Cleanup: remove handlers to release file locks
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    def test_setup_logger_rotating_handler(self):
        """Test that rotating file handler is configured"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = os.path.join(tmpdir, "test.log")
            logger = setup_logger(logfile)
            
            # Check for RotatingFileHandler
            has_rotating_handler = any(
                hasattr(h, 'maxBytes') for h in logger.handlers
            )
            assert has_rotating_handler
            
            # Cleanup: remove handlers to release file locks
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


class TestNewFileHandler:
    """Test suite for NewFileHandler class"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories"""
        watch_dir = tempfile.mkdtemp()
        processed_dir = tempfile.mkdtemp()
        yield watch_dir, processed_dir
        shutil.rmtree(watch_dir, ignore_errors=True)
        shutil.rmtree(processed_dir, ignore_errors=True)

    def test_handler_ignores_directories(self, mock_logger):
        """Test that on_created ignores directory events"""
        handler = NewFileHandler(mock_logger)
        
        # Mock event for directory
        event = Mock()
        event.is_directory = True
        event.src_path = "/some/dir"
        
        handler.on_created(event)
        
        # Logger should not be called for directories
        mock_logger.info.assert_not_called()

    def test_handler_detects_new_file(self, mock_logger, temp_dirs):
        """Test that on_created detects new files"""
        watch_dir, processed_dir = temp_dirs
        handler = NewFileHandler(
            mock_logger,
            processed_dir=processed_dir,
            settle_seconds=0.01,
            max_tries=2
        )
        
        # Create a test file
        test_file = os.path.join(watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("content")
        
        # Mock event
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        handler.on_created(event)
        
        # Should log that file was detected
        assert any("New file detected" in str(call) for call in mock_logger.info.call_args_list)

    def test_handler_waits_for_file_stability(self, mock_logger, temp_dirs):
        """Test that handler waits for file size to stabilize"""
        watch_dir, processed_dir = temp_dirs
        handler = NewFileHandler(
            mock_logger,
            processed_dir=processed_dir,
            settle_seconds=0.01,
            max_tries=5
        )
        
        test_file = os.path.join(watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("stable content")
        
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        handler.on_created(event)
        
        # Should log stable file
        assert any("New file detected" in str(call) for call in mock_logger.info.call_args_list)

    def test_handler_processes_file(self, mock_logger, temp_dirs):
        """Test that handler processes files when processed_dir is set"""
        watch_dir, processed_dir = temp_dirs
        handler = NewFileHandler(
            mock_logger,
            processed_dir=processed_dir,
            settle_seconds=0.01,
            max_tries=2
        )
        
        test_file = os.path.join(watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("content")
        
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        handler.on_created(event)
        
        # File should be moved to processed_dir
        assert os.path.exists(os.path.join(processed_dir, "test.txt"))

    def test_handler_skips_processing_without_processed_dir(self, mock_logger, temp_dirs):
        """Test that handler skips processing when processed_dir is None"""
        watch_dir, _ = temp_dirs
        handler = NewFileHandler(
            mock_logger,
            processed_dir=None,
            settle_seconds=0.01,
            max_tries=2
        )
        
        test_file = os.path.join(watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("content")
        
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        handler.on_created(event)
        
        # Should log skip message
        assert any("skipping processing" in str(call).lower() for call in mock_logger.info.call_args_list)
        # Original file should still exist
        assert os.path.exists(test_file)

    def test_handler_handles_processing_errors(self, mock_logger, temp_dirs):
        """Test that handler logs errors during processing"""
        watch_dir, processed_dir = temp_dirs
        handler = NewFileHandler(
            mock_logger,
            processed_dir=processed_dir,
            settle_seconds=0.01,
            max_tries=2
        )
        
        # Create file but make it inaccessible to cause error
        test_file = os.path.join(watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("content")
        
        # Mock process_new_file to raise an exception
        with patch('watcher.process_new_file', side_effect=Exception("Test error")):
            event = Mock()
            event.is_directory = False
            event.src_path = test_file
            
            # Should handle exception gracefully
            handler.on_created(event)
        
        # Should log exception
        assert mock_logger.exception.called


class TestParseArgs:
    """Test suite for parse_args function"""

    def test_parse_args_defaults(self):
        """Test that parse_args returns default values"""
        with patch('sys.argv', ['watcher.py']):
            args = parse_args()
            
            assert args.path == r"D:\Data Engineering\Data\DataIn"
            assert args.logdir == r"D:\Data Engineering\Data\Logs"
            assert args.processed == r"D:\Data Engineering\Data\Processed"
            assert args.settle == 0.5
            assert args.tries == 10

    def test_parse_args_custom_path(self):
        """Test that parse_args accepts custom path"""
        with patch('sys.argv', ['watcher.py', '--path', 'C:\\custom\\path']):
            args = parse_args()
            assert args.path == 'C:\\custom\\path'

    def test_parse_args_short_flags(self):
        """Test that parse_args accepts short flags"""
        with patch('sys.argv', ['watcher.py', '-p', 'C:\\path', '-l', 'C:\\logs', '-d', 'C:\\proc']):
            args = parse_args()
            assert args.path == 'C:\\path'
            assert args.logdir == 'C:\\logs'
            assert args.processed == 'C:\\proc'

    def test_parse_args_settle_and_tries(self):
        """Test that parse_args accepts settle and tries parameters"""
        with patch('sys.argv', ['watcher.py', '--settle', '1.5', '--tries', '20']):
            args = parse_args()
            assert args.settle == 1.5
            assert args.tries == 20
