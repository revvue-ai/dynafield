import re
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def parse_structured_traceback(exception: Optional[Exception] = None, tb_string: Optional[str] = None, repository: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse traceback into structured data with full stack trace.

    Args:
        exception: Exception object (optional)
        tb_string: Pre-formatted traceback string (optional)
        repository: GitHub repository URL (e.g., "org/repo-name")

    Returns:
        Dict with structured traceback information
    """
    # Get traceback string if not provided
    if tb_string is None:
        if exception is not None:
            try:
                tb_string = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            except Exception:
                tb_string = traceback.format_exc()
        else:
            # Get current exception
            exc_info = sys.exc_info()
            if exc_info[0] is not None:
                tb_string = "".join(traceback.format_exception(*exc_info))
            else:
                # No active exception, return empty structure
                return create_empty_traceback_structure(repository)

    # Ensure tb_string is not None after the above logic
    tb_string = tb_string or ""

    lines = [line.rstrip() for line in tb_string.split("\n") if line.strip()]

    structured: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": repository,
        "exception": {"type": None, "message": None, "full_type": None},
        "root_cause": {"file": None, "line": None, "function": None, "code_snippet": None, "github_url": None},
        "stack_trace": [],
        "raw_traceback": tb_string.strip(),
    }

    current_frame: Dict[str, Any] = {}
    i = 0
    line_count = len(lines)

    while i < line_count:
        line = lines[i]

        # Skip traceback header
        if line == "Traceback (most recent call last):":
            i += 1
            continue

        # Match file line pattern: File "path", line X, in function
        file_match = re.match(r'File\s+"([^"]+)"\s*,\s*line\s+(\d+)\s*,\s*in\s+([^\n]+)', line)
        if file_match:
            # Save previous frame if exists
            if current_frame:
                structured["stack_trace"].append(current_frame)
                current_frame = {}

            file_path, line_no, function_name = file_match.groups()

            current_frame = {
                "file": {
                    "full_path": file_path,
                    "relative_path": extract_relative_path(file_path),
                    "filename": extract_filename(file_path),
                    "github_url": create_github_url(repository, file_path, int(line_no)) if repository else None,
                },
                "line_number": int(line_no),
                "function": function_name.strip(),
                "code": None,
            }

            # Look for code in next line(s) - handle the caret lines
            i += 1
            code_lines: List[str] = []
            while i < line_count:
                next_line = lines[i].strip()

                # Stop if we hit another file line or exception line
                if next_line.startswith("File ") or (":" in next_line and not next_line.startswith(" ") and not next_line.startswith("^")):
                    break

                # Skip lines that are just carets (^^^) - these are code pointers
                if next_line and not all(c in "^ " for c in next_line):
                    code_lines.append(next_line)

                i += 1

            if code_lines:
                current_frame["code"] = "\n".join(code_lines)

            # Continue to next iteration (i already incremented)
            continue

        # Match exception line (various formats)
        if not line.startswith("File ") and not line.startswith("  ") and ":" in line and not all(c in "^ " for c in line):
            # Handle different exception formats
            if " - " in line:  # Some frameworks format differently
                parts = line.split(" - ", 1)
                exc_type = parts[0].strip()
                exc_message = parts[1].strip() if len(parts) > 1 else ""
            else:
                parts = line.split(":", 1)
                exc_type = parts[0].strip()
                exc_message = parts[1].strip() if len(parts) > 1 else ""

            structured["exception"]["type"] = exc_type
            structured["exception"]["message"] = exc_message
            structured["exception"]["full_type"] = line.strip()

        i += 1

    # Add the last frame if it exists
    if current_frame:
        structured["stack_trace"].append(current_frame)

    # If we didn't find frames with the regex, try a more direct approach
    if not structured["stack_trace"]:
        structured["stack_trace"] = extract_frames_directly(tb_string, repository)

    # Generate root_cause information
    if structured["stack_trace"]:
        # Root cause is the last frame (where exception was raised)
        root_frame = structured["stack_trace"][-1]
        structured["root_cause"] = {
            "file": root_frame["file"]["relative_path"],
            "line": root_frame["line_number"],
            "function": root_frame["function"],
            "code_snippet": root_frame["code"],
            "github_url": root_frame["file"]["github_url"],
        }

    # If we still don't have exception info but have frames, try to extract from the raw traceback
    if not structured["exception"]["type"] and structured["stack_trace"]:
        # Look for exception in the last few lines of raw traceback
        last_lines = tb_string.strip().split("\n")[-3:]
        for line in reversed(last_lines):
            line = line.strip()
            if ":" in line and not line.startswith("File ") and not line.startswith("  ") and not all(c in "^ " for c in line):
                parts = line.split(":", 1)
                structured["exception"]["type"] = parts[0].strip()
                structured["exception"]["message"] = parts[1].strip() if len(parts) > 1 else ""
                structured["exception"]["full_type"] = line
                break

    return structured


def create_github_url(repository: Optional[str], file_path: str, line_number: int) -> Optional[str]:
    """
    Create GitHub URL for the specific file and line number.

    Args:
        repository: GitHub repo in format "owner/repo"
        file_path: Full file path from traceback
        line_number: Line number where error occurred

    Returns:
        GitHub URL string or None if repository is None
    """
    if repository is None:
        return None

    # Extract the relative path from the project
    relative_path = extract_relative_path(file_path)

    # You might want to adjust the branch name (main, master, develop, etc.)
    branch = "main"  # or get this from config

    # Convert Windows paths to Unix-style for URLs
    relative_path = relative_path.replace("\\", "/")

    return f"https://github.com/{repository}/blob/{branch}/{relative_path}#L{line_number}"


def extract_frames_directly(tb_string: str, repository: Optional[str] = None) -> List[Dict[str, Any]]:
    """Alternative method to extract frames directly from traceback string"""
    frames: List[Dict[str, Any]] = []
    lines = tb_string.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for file lines
        if line.startswith('File "'):
            # Extract file path, line number, and function name manually
            file_part = line[5:]  # Remove 'File '

            # Find the closing quote for file path
            quote_end = file_part.find('",')
            if quote_end == -1:
                i += 1
                continue

            file_path = file_part[:quote_end]
            remaining = file_part[quote_end + 2 :].strip()  # After '",'

            # Extract line number
            if remaining.startswith("line "):
                line_part = remaining[5:]  # Remove 'line '
                comma_pos = line_part.find(",")
                if comma_pos != -1:
                    line_no = line_part[:comma_pos]
                    function_part = line_part[comma_pos + 1 :].strip()

                    if function_part.startswith("in "):
                        function_name = function_part[3:].strip()  # Remove 'in '

                        frame: Dict[str, Any] = {
                            "file": {
                                "full_path": file_path,
                                "relative_path": extract_relative_path(file_path),
                                "filename": extract_filename(file_path),
                                "github_url": create_github_url(repository, file_path, int(line_no)),
                            },
                            "line_number": int(line_no),
                            "function": function_name,
                            "code": None,
                        }

                        # Look for code in next lines
                        i += 1
                        code_lines: List[str] = []
                        while i < len(lines):
                            code_line = lines[i].strip()
                            # Stop if we hit another file or exception
                            if code_line.startswith("File ") or (":" in code_line and not code_line.startswith(" ") and not all(c in "^ " for c in code_line)):
                                break
                            # Skip caret lines
                            if code_line and not all(c in "^ " for c in code_line):
                                code_lines.append(code_line)
                            i += 1

                        if code_lines:
                            frame["code"] = "\n".join(code_lines)

                        frames.append(frame)
                        continue
        i += 1

    return frames


def extract_relative_path(full_path: str) -> str:
    """Extract relative path from project structure"""
    patterns = ["src\\", "src/", "app\\", "app/"]

    for pattern in patterns:
        if pattern in full_path:
            parts = full_path.split(pattern)
            if len(parts) > 1:
                return parts[-1]

    return full_path


def extract_filename(full_path: str) -> str:
    """Extract just the filename from full path"""
    if "\\" in full_path:
        return full_path.split("\\")[-1]
    elif "/" in full_path:
        return full_path.split("/")[-1]
    return full_path


def create_empty_traceback_structure(repository: Optional[str] = None) -> Dict[str, Any]:
    """Create empty traceback structure when no exception is active"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": repository,
        "exception": {"type": "Unknown", "message": "No active exception", "full_type": "Unknown: No active exception"},
        "root_cause": {"file": None, "line": None, "function": None, "code_snippet": None, "github_url": None},
        "stack_trace": [],
        "raw_traceback": "No traceback available",
    }
