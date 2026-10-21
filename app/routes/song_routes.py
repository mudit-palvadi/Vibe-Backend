import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.config import settings
from app.middleware.auth_middleware import get_current_user
from app.repositories.dependencies import get_favourite_repository, get_song_repository
from app.repositories.protocols import FavouriteRepository, SongRepository
from app.repositories.records import UserRecord
from app.schemas.favourite import FavouriteSong
from app.schemas.song import FavouriteToggleResponse, SongResponse, SongUploadResponse
from app.schemas.user import FavouriteResponse

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
