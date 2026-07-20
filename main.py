from app import create_app
from app.config import HOST, PORT

app = create_app()

if __name__ == "__main__":
    import uvicorn

    print(f"\n  Crashout Recovery at http://{HOST}:{PORT}\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
