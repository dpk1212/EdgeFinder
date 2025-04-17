from fastapi import FastAPI

app = FastAPI()

@app.get("/api_py")
async def read_root():
    """
    Root endpoint for the Python API.
    Confirms the Python API is running.
    """
    return {"message": "Python API is running!"}

@app.get("/api_py/test_pybaseball")
async def test_pybaseball_import():
    """
    Endpoint to test if pybaseball can be imported successfully.
    """
    try:
        # Try importing a specific function or module from pybaseball
        from pybaseball import statcast 
        # You could optionally call a simple pybaseball function here if needed
        # For now, just importing is a good test
        return {"message": "pybaseball imported successfully!"}
    except ImportError as e:
        return {"error": f"Failed to import pybaseball: {e}"}
    except Exception as e:
        # Catch any other potential errors during import or usage
        return {"error": f"An unexpected error occurred: {e}"}

# Note: Vercel automatically handles running the app
# You don't need the uvicorn.run() part for deployment
