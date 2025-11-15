"""Tests for processors.file_processor module"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from processors.file_processor import process_new_file


class TestProcessNewFile:
    """Test suite for process_new_file function"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        source_dir = tempfile.mkdtemp()
        processed_dir = tempfile.mkdtemp()
        yield source_dir, processed_dir
        # Cleanup
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(processed_dir, ignore_errors=True)

    def test_process_new_file_simple(self, temp_dirs):
        """Test basic file movement"""
        source_dir, processed_dir = temp_dirs
        source_file = os.path.join(source_dir, "test_file.txt")
        
        # Create test file
        with open(source_file, "w") as f:
            f.write("test content")
        
        # Process file
        dest = process_new_file(source_file, processed_dir)
        
        # Assert file was moved
        assert os.path.exists(dest)
        assert not os.path.exists(source_file)
        assert os.path.dirname(dest) == processed_dir
        assert os.path.basename(dest) == "test_file.txt"

    def test_process_new_file_creates_processed_dir(self, temp_dirs):
        """Test that processed_dir is created if it doesn't exist"""
        source_dir, processed_dir = temp_dirs
        nonexistent_dir = os.path.join(processed_dir, "subdir")
        
        source_file = os.path.join(source_dir, "test_file.txt")
        with open(source_file, "w") as f:
            f.write("content")
        
        dest = process_new_file(source_file, nonexistent_dir)
        
        assert os.path.exists(nonexistent_dir)
        assert os.path.exists(dest)

    def test_process_new_file_handles_duplicates(self, temp_dirs):
        """Test that duplicate filenames get numeric suffixes"""
        source_dir, processed_dir = temp_dirs
        
        # Create first file and move it
        file1 = os.path.join(source_dir, "duplicate.txt")
        with open(file1, "w") as f:
            f.write("file 1")
        
        dest1 = process_new_file(file1, processed_dir)
        assert os.path.basename(dest1) == "duplicate.txt"
        
        # Create second file with same name and move it
        file2 = os.path.join(source_dir, "duplicate.txt")
        with open(file2, "w") as f:
            f.write("file 2")
        
        dest2 = process_new_file(file2, processed_dir)
        assert os.path.basename(dest2) == "duplicate-1.txt"
        
        # Both files should exist
        assert os.path.exists(dest1)
        assert os.path.exists(dest2)
        assert dest1 != dest2

    def test_process_new_file_handles_multiple_duplicates(self, temp_dirs):
        """Test that multiple duplicates get correct numeric suffixes"""
        source_dir, processed_dir = temp_dirs
        
        destinations = []
        for i in range(3):
            file_path = os.path.join(source_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write(f"content {i}")
            dest = process_new_file(file_path, processed_dir)
            destinations.append(dest)
        
        # Check naming pattern
        assert os.path.basename(destinations[0]) == "test.txt"
        assert os.path.basename(destinations[1]) == "test-1.txt"
        assert os.path.basename(destinations[2]) == "test-2.txt"
        
        # All should exist
        for dest in destinations:
            assert os.path.exists(dest)

    def test_process_new_file_with_extension(self, temp_dirs):
        """Test that file extensions are handled correctly"""
        source_dir, processed_dir = temp_dirs
        
        file_path = os.path.join(source_dir, "data.csv")
        with open(file_path, "w") as f:
            f.write("col1,col2\n1,2")
        
        dest = process_new_file(file_path, processed_dir)
        
        assert dest.endswith(".csv")
        assert os.path.exists(dest)

    def test_process_new_file_preserves_content(self, temp_dirs):
        """Test that file content is preserved after moving"""
        source_dir, processed_dir = temp_dirs
        test_content = "This is test content\nLine 2\nLine 3"
        
        file_path = os.path.join(source_dir, "content_test.txt")
        with open(file_path, "w") as f:
            f.write(test_content)
        
        dest = process_new_file(file_path, processed_dir)
        
        with open(dest, "r") as f:
            read_content = f.read()
        
        assert read_content == test_content

    def test_process_new_file_with_logger(self, temp_dirs):
        """Test that logger is called without raising exceptions"""
        source_dir, processed_dir = temp_dirs
        
        # Mock logger
        class MockLogger:
            def __init__(self):
                self.messages = []
            
            def info(self, msg, *args):
                self.messages.append((msg, args))
        
        logger = MockLogger()
        file_path = os.path.join(source_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("content")
        
        dest = process_new_file(file_path, processed_dir, logger=logger)
        
        assert len(logger.messages) > 0
        assert "Moved file to processed dir" in logger.messages[0][0]

    def test_process_new_file_logger_exception_handling(self, temp_dirs):
        """Test that file processing continues even if logger fails"""
        source_dir, processed_dir = temp_dirs
        
        # Mock logger that raises exception
        class FailingLogger:
            def info(self, msg, *args):
                raise Exception("Logger failed")
        
        logger = FailingLogger()
        file_path = os.path.join(source_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("content")
        
        # Should not raise exception
        dest = process_new_file(file_path, processed_dir, logger=logger)
        assert os.path.exists(dest)
