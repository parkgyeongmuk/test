"""Image hosting (Imgur) + Instagram Graph API publishing helpers."""

import time

import requests

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


def upload_to_imgur(image_path: str, client_id: str) -> str:
    """Upload an image anonymously to Imgur and return its public URL."""
    with open(image_path, "rb") as f:
        resp = requests.post(
            IMGUR_UPLOAD_URL,
            headers={"Authorization": f"Client-ID {client_id}"},
            files={"image": f},
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Imgur upload failed: {data}")
    return data["data"]["link"]


def create_media_container(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _wait_until_ready(creation_id: str, access_token: str, timeout_s: int = 60) -> None:
    """Poll the container's status until Instagram has finished fetching the image."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram failed to process media container {creation_id}")
        time.sleep(3)
    raise TimeoutError(f"Media container {creation_id} not ready after {timeout_s}s")


def publish_media(ig_user_id: str, access_token: str, creation_id: str) -> str:
    _wait_until_ready(creation_id, access_token)
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def post_image(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """Full publish flow: create container, wait, publish. Returns the new media id."""
    creation_id = create_media_container(ig_user_id, access_token, image_url, caption)
    return publish_media(ig_user_id, access_token, creation_id)
