import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.core.config import settings
from app.middleware.auth_middleware import get_current_user
from app.repositories.dependencies import get_favourite_repository, get_song_repository
from app.repositories.protocols import FavouriteRepository, SongRepository
from app.repositories.records import UserRecord
from app.schemas.favourite import FavouriteSong
from app.schemas.song import (
    FavouriteToggleResponse,
    SongResponse,
    SongUploadResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.schemas.user import FavouriteResponse
from app.storage.s3 import (
    build_temp_key,
    copy_to_final_place,
    create_upload_url,
    guess_content_type,
    is_temp_key,
    media_url,
    object_exists,
)

router = APIRouter(prefix="/song", tags=["Upload Song"])

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


@router.post("/upload", status_code=201, response_model=SongUploadResponse)
def upload_song(
    song_audio: UploadFile = File(...),
    thumbnail: UploadFile = File(...),
    artist: str = Form(...),
    song_name: str = Form(...),
    tags: str = Form(...),
    songs: SongRepository = Depends(get_song_repository),
    auth_user: UserRecord = Depends(get_current_user),
):
    if not settings.LEGACY_UPLOAD_ENABLED:
        raise HTTPException(status_code=404, detail="The old upload endpoint is turned off")

    song_id = str(uuid.uuid4())
    song_upload_response = cloudinary.uploader.upload(
        song_audio.file, resource_type="auto", folder=f"songs/{song_id}"
    )
    thumbnail_upload_response = cloudinary.uploader.upload(
        thumbnail.file, resource_type="image", folder=f"songs/{song_id}"
    )

    new_song = songs.create(
        song_id=song_id,
        song_name=song_name,
        artist=artist,
        tags=tags,
        song_url=song_upload_response["url"],
        thumbnail_url=thumbnail_upload_response["url"],
    )

    return {
        "message": "Song uploaded successfully",
        "song": {
            "id": new_song.id,
            "song_name": new_song.song_name,
            "artist": new_song.artist,
            "song_url": new_song.song_url,
            "thumbnail_url": new_song.thumbnail_url,
            "tags": new_song.tags,
        },
    }


@router.post("/upload-init", status_code=201, response_model=UploadInitResponse)
def upload_init(
    request: UploadInitRequest,
    auth_user: UserRecord = Depends(get_current_user),
):
    song_id = str(uuid.uuid4())

    return {
        "song_id": song_id,
        "audio": create_upload_url(
            build_temp_key(song_id, request.audio_filename, "audio"),
            guess_content_type(request.audio_filename),
        ),
        "thumbnail": create_upload_url(
            build_temp_key(song_id, request.thumbnail_filename, "thumbnail"),
            guess_content_type(request.thumbnail_filename),
        ),
        "expires_in": settings.S3_UPLOAD_URL_EXPIRY,
    }


@router.post("/upload-complete", status_code=201, response_model=UploadCompleteResponse)
def upload_complete(
    request: UploadCompleteRequest,
    songs: SongRepository = Depends(get_song_repository),
    auth_user: UserRecord = Depends(get_current_user),
):
    if not is_temp_key(request.audio_key, request.song_id) or not is_temp_key(
        request.thumbnail_key, request.song_id
    ):
        raise HTTPException(status_code=400, detail="The upload keys do not belong to this song")

    if not object_exists(request.audio_key) or not object_exists(request.thumbnail_key):
        raise HTTPException(status_code=404, detail="The files are not in the bucket yet")

    audio_key = copy_to_final_place(request.audio_key)
    thumbnail_key = copy_to_final_place(request.thumbnail_key)

    song = songs.create(
        song_id=request.song_id,
        song_name=request.song_name,
        artist=request.artist,
        tags=request.tags,
        song_url=media_url(audio_key),
        thumbnail_url=media_url(thumbnail_key),
    )

    return {"message": "Song uploaded successfully", "song": song}


@router.get("/list", status_code=200, response_model=list[SongResponse])
def fetchSongs(
    songs: SongRepository = Depends(get_song_repository),
    auth_details: UserRecord = Depends(get_current_user),
):
    return songs.list_all()


@router.get("/search", response_model=list[SongResponse])
def search_songs(
    q: str = Query(..., min_length=1),
    songs: SongRepository = Depends(get_song_repository),
    auth_details: UserRecord = Depends(get_current_user),
):
    return songs.search(q)


@router.post("/favourite", status_code=201, response_model=FavouriteToggleResponse)
def favouriteSong(
    fav_song: FavouriteSong,
    favourites: FavouriteRepository = Depends(get_favourite_repository),
    auth_details: UserRecord = Depends(get_current_user),
):
    is_favourite = favourites.toggle(song_id=fav_song.song_id, user_id=str(auth_details.id))

    return {"message": is_favourite}


@router.get("/list-favourites", status_code=200, response_model=list[FavouriteResponse])
def fetchFavSongs(
    favourites: FavouriteRepository = Depends(get_favourite_repository),
    auth_details: UserRecord = Depends(get_current_user),
):
    return favourites.list_for_user(str(auth_details.id))
