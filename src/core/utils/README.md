# Utils Module

Utility functions for MAX AI.

## TextSanitizer

Cleans model output from artifacts using regex patterns.

### Patterns

| Pattern | Removes |
|---------|---------|
| `***+` | Multiple asterisks → `**` |
| `User:$` | Trailing "User:" artifact |
| `\n{3,}` | Excessive newlines → `\n\n` |
| `[\u4e00-\u9fff]+$` | Chinese chars at end |
| `<\|im_end\|>` | Special tokens |

### Usage

```python
from src.core.utils import sanitizer

# Full cleanup (before saving)
clean = sanitizer.clean_output(raw_text)

# Stream cleanup (for SSE)
chunk = sanitizer.stream_cleaner(chunk)

# Trailing only
clean = sanitizer.remove_trailing_artifacts(text)
```

### Integration

- `chat.py`: `stream_cleaner()` on SSE chunks
- `chat.py`: `clean_output()` before memory.add_message()
