from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import get_current_user
from app.repositories.dependencies import get_playlist_repository, get_song_repository
from app.repositories.errors import DuplicateSongError, SongNotFoundError
from app.repositories.protocols import PlaylistRepository, SongRepository
from app.repositories.records import UserRecord
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
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    return playlists.create(
        user_id=str(current_user.id),
        name=playlist_data.name,
        description=playlist_data.description,
        thumbnail_url=playlist_data.thumbnail_url,
    )


@router.get("/list", response_model=list[PlaylistResponse])
def get_user_playlists(
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    return playlists.list_for_user(current_user.id)


@router.get("/{playlist_id}", response_model=PlaylistWithSongsResponse)
def get_playlist_details(
    playlist_id: UUID,
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    playlist = playlists.get(str(playlist_id))
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return {**asdict(playlist), "songs": playlists.list_songs(playlist.id)}


@router.post("/add-song", status_code=status.HTTP_201_CREATED)
def add_song_to_playlist(
    data: AddPlaylistSong,
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    songs: SongRepository = Depends(get_song_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    # Verify playlist ownership
    playlist = playlists.get(str(data.playlist_id))
    if not playlist or playlist.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    # Verify song exists
    if not songs.get(data.song_id):
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        playlists.add_song(playlist_id=playlist.id, song_id=data.song_id)
    except SongNotFoundError:
        raise HTTPException(status_code=404, detail="Song not found") from None
    except DuplicateSongError:
        raise HTTPException(status_code=400, detail="Song is already in the playlist") from None

    return {"message": "Song added to playlist successfully"}


@router.delete("/remove-song", status_code=status.HTTP_200_OK)
def remove_song_from_playlist(
    data: AddPlaylistSong,
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    playlist = playlists.get(str(data.playlist_id))
    if not playlist or playlist.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    if not playlists.remove_song(playlist_id=playlist.id, song_id=data.song_id):
        raise HTTPException(status_code=404, detail="Song relation not found in this playlist")

    return {"message": "Song removed from playlist successfully"}


@router.delete("/{playlist_id}", status_code=status.HTTP_200_OK)
def delete_playlist(
    playlist_id: UUID,
    playlists: PlaylistRepository = Depends(get_playlist_repository),
    current_user: UserRecord = Depends(get_current_user),
):
    playlist = playlists.get(str(playlist_id))
    if not playlist or playlist.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Playlist not found or access denied")

    playlists.delete(playlist.id)
    return {"message": "Playlist deleted successfully"}
