from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.database import get_session
from app.middleware.auth_middleware import get_current_user
from app.models.playlist import Playlist, PlaylistSongLink
from app.models.song import Song
from app.models.user import User
from app.schemas.playlist import (
    AddPlaylistSong,
    PlaylistCreate,
    PlaylistResponse,
    PlaylistWithSongsResponse,
)

router = APIRouter(prefix="/playlist", tags=["Playlists"])


@router.post("/create", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    playlist_data: PlaylistCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    playlist = Playlist(
        user_id=current_user.id,
        name=playlist_data.name,
        description=playlist_data.description,
        thumbnail_url=playlist_data.thumbnail_url,
    )
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    return playlist


@router.get("/list", response_model=list[PlaylistResponse])
def get_user_playlists(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Playlist).where(Playlist.user_id == current_user.id)
    return session.exec(statement).all()


@router.get("/{playlist_id}", response_model=PlaylistWithSongsResponse)
def get_playlist_details(
    playlist_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    playlist = session.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return playlist


@router.post("/add-song", status_code=status.HTTP_201_CREATED)
def add_song_to_playlist(
    data: AddPlaylistSong,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Verify playlist ownership
    playlist = session.get(Playlist, data.playlist_id)
    if not playlist or playlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    # Verify song exists
    song = session.get(Song, data.song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Check for duplicate additions
    dup_statement = select(PlaylistSongLink).where(
        PlaylistSongLink.playlist_id == data.playlist_id,
        PlaylistSongLink.song_id == data.song_id,
    )
    existing_entry = session.exec(dup_statement).first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="Song is already in the playlist")

    # Save mapping
    link = PlaylistSongLink(playlist_id=data.playlist_id, song_id=data.song_id)
    session.add(link)
    session.commit()
    return {"message": "Song added to playlist successfully"}


@router.delete("/remove-song", status_code=status.HTTP_200_OK)
def remove_song_from_playlist(
    data: AddPlaylistSong,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    playlist = session.get(Playlist, data.playlist_id)
    if not playlist or playlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    statement = select(PlaylistSongLink).where(
        PlaylistSongLink.playlist_id == data.playlist_id,
        PlaylistSongLink.song_id == data.song_id,
    )
    entry = session.exec(statement).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Song relation not found in this playlist")

    session.delete(entry)
    session.commit()
    return {"message": "Song removed from playlist successfully"}


@router.delete("/{playlist_id}", status_code=status.HTTP_200_OK)
def delete_playlist(
    playlist_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    playlist = session.get(Playlist, playlist_id)
    if not playlist or playlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    session.delete(playlist)
    session.commit()
    return {"message": "Playlist deleted successfully"}
