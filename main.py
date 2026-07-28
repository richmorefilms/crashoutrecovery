from app import create_app
from app.config import HOST, PORT

# App factory registers all routers (auth, youtube, stories, ads, TikTok, …).
# TikTok routes live in app/tiktok_routes.py and are included inside create_app().
app = create_app()

if __name__ == "__main__":
    import uvicorn

    print(f"\n  Crashout Recovery at http://{HOST}:{PORT}\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
