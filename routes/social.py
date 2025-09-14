# routes/social.py
from fastapi import APIRouter, HTTPException
from models.social import ListResponse, SocialRenderRequest, SocialRenderResponse
from services.social_card import render_twitter, render_instagram, render_image_to_data_url

social_router = APIRouter(prefix="/social", tags=["Social Mock"])

@social_router.get("/templates", response_model=ListResponse)
def list_templates():
    return ListResponse(items=["twitter", "instagram"])

@social_router.post("/render", response_model=SocialRenderResponse)
def render_card(req: SocialRenderRequest):
    try:
        if req.platform == "twitter":
            img = render_twitter(
                theme=req.theme,
                display_name=req.display_name or req.username,
                username=req.username.lstrip("@"),
                verified=req.verified,
                text=req.text,
                avatar_url=str(req.avatar_url) if req.avatar_url else None,
                comments=req.comments or 0,
                reposts=req.reposts or 0,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
            )
        else:
            img = render_instagram(
                theme=req.theme,
                username=req.username,
                text=req.text,
                avatar_url=str(req.avatar_url) if req.avatar_url else None,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
                location=req.location,
            )
        return SocialRenderResponse(image_data_url=render_image_to_data_url(img))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render failed: {e}")
