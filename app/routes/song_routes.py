import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import joinedload
from sqlmodel import Session, or_, select

from app.core.config import settings
from app.db.database import get_session
from app.middleware.auth_middleware import get_current_user
from app.models.favourite import Favourite
from app.models.song import Song
from app.models.user import User
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
    db: Session = Depends(get_session),
    auth_user: User = Depends(get_current_user),
):
    song_id = str(uuid.uuid4())
    song_upload_response = cloudinary.uploader.upload(
        song_audio.file, resource_type="auto", folder=f"songs/{song_id}"
    )
    thumbnail_upload_response = cloudinary.uploader.upload(
        thumbnail.file, resource_type="image", folder=f"songs/{song_id}"
    )

    new_song = Song(
        id=song_id,
        song_name=song_name,
        artist=artist,
        tags=tags,
        song_url=song_upload_response["url"],
        thumbnail_url=thumbnail_upload_response["url"],
    )

    db.add(new_song)
    db.commit()
    db.refresh(new_song)

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
def fetchSongs(db: Session = Depends(get_session), auth_details: User = Depends(get_current_user)):
    songs = db.exec(select(Song)).all()
    return songs


@router.get("/search", response_model=list[SongResponse])
def search_songs(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_session),
    auth_details: User = Depends(get_current_user),
):

    statement = select(Song).where(
        or_(
            Song.song_name.ilike(f"%{q}%"),
            Song.artist.ilike(f"%{q}%"),
            Song.tags.ilike(f"%{q}%"),
        )
    )
    results = db.exec(statement).all()
    return results


@router.post("/favourite", status_code=201, response_model=FavouriteToggleResponse)
def favouriteSong(
    fav_song: FavouriteSong,
    db: Session = Depends(get_session),
    auth_details: User = Depends(get_current_user),
):
    user_id = auth_details.id

    fav_song_res = db.exec(
        select(Favourite).where(Favourite.song_id == fav_song.song_id, Favourite.user_id == user_id)
    ).first()

    if fav_song_res:
        db.delete(fav_song_res)
        db.commit()

        return {"message": False}
    else:
        new_fav = Favourite(id=str(uuid.uuid4()), song_id=fav_song.song_id, user_id=user_id)
        db.add(new_fav)
        db.commit()
        return {"message": True}


@router.get("/list-favourites", status_code=200, response_model=list[FavouriteResponse])
def fetchFavSongs(
    db: Session = Depends(get_session), auth_details: User = Depends(get_current_user)
):
    user_id = auth_details.id
    fav_songs = db.exec(
        select(Favourite).where(Favourite.user_id == user_id).options(joinedload(Favourite.song))
    ).all()
    return fav_songs
