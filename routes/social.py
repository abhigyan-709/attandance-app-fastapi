from io import BytesIO
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.social import ListResponse, SocialRenderRequest, SocialRenderResponse
from services.social_card import (
    render_twitter,
    render_instagram,
    render_image_to_data_url,
)

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
                avatar_url=req.avatar_url,
                comments=req.comments or 0,
                reposts=req.reposts or 0,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
            )
        else:
            img = render_instagram(
                theme=req.theme,
                username=req.username.lstrip("@"),
                text=req.text,
                avatar_url=req.avatar_url,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
                location=req.location,
                photo_url=req.photo_url,
                width=req.width or 900,
            )
        return SocialRenderResponse(image_data_url=render_image_to_data_url(img))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")

@social_router.post("/render/png")
def render_card_png(req: SocialRenderRequest):
    try:
        if req.platform == "twitter":
            img = render_twitter(
                theme=req.theme,
                display_name=req.display_name or req.username,
                username=req.username.lstrip("@"),
                verified=req.verified,
                text=req.text,
                avatar_url=req.avatar_url,
                comments=req.comments or 0,
                reposts=req.reposts or 0,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
            )
        else:
            img = render_instagram(
                theme=req.theme,
                username=req.username.lstrip("@"),
                text=req.text,
                avatar_url=req.avatar_url,
                likes=req.likes or 0,
                minutes_ago=req.minutes_ago or 5,
                location=req.location,
                photo_url=req.photo_url,
                width=req.width or 900,
            )

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={"Content-Disposition": 'inline; filename="social-mock.png"'},
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")
