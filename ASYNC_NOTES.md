# Asynchronous Operations Notes

## Current Implementation
The application currently uses threading for asynchronous operations (e.g., `threading.Thread` for AI API calls and GitHub repository fetching).

## Future Considerations
For more complex asynchronous operations, consider migrating to `asyncio`:

### Benefits of asyncio:
- Better resource management for I/O-bound operations
- More efficient handling of multiple concurrent API calls
- Native support for async/await patterns
- Better integration with async HTTP libraries (e.g., `aiohttp`, `httpx`)

### Migration Path:
1. Replace `threading.Thread` with `asyncio.create_task()`
2. Use `asyncio.run()` or `asyncio.get_event_loop()` for event loop management
3. Convert synchronous functions to async functions
4. Use async HTTP clients for API calls (e.g., `aiohttp` for DeepSeek, async Gemini SDK if available)
5. Use `tkinter.after()` to schedule async operations on the main thread

### Example Structure:
```python
import asyncio
import aiohttp

async def fetch_ai_response_async(prompt: str):
    async with aiohttp.ClientSession() as session:
        # Make async API call
        pass

def schedule_async_task(coro):
    """Schedule an async coroutine to run in the background."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(coro)
    # Use tkinter.after to update UI when done
```

### Current Threading Approach:
The current threading approach is sufficient for the current use case. Consider asyncio when:
- You need to handle 10+ concurrent operations
- You want better resource efficiency
- You plan to integrate with async-first libraries
