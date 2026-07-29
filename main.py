from app import create_app
from app.config import HOST, PORT

# App factory registers all routers (auth, youtube, stories, ads, TikTok, feed, oauth, creator, …).
# TikTok: app/tiktok_routes.py → /api/tiktok/*
# YouTube: app/youtube_routes.py → /api/youtube/* (including GET /api/youtube/feed)
# Unified feed: app/feed_routes.py → /api/feed/*
# Router include lives in create_app() — do not double-register here with a second prefix.
app = create_app()

if __name__ == "__main__":
    import uvicorn

    print(f"\n  Crashout Recovery at http://{HOST}:{PORT}\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
