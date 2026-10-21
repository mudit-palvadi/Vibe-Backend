from pydantic import BaseModel


class SongResponse(BaseModel):
    id: str
    song_name: str
    artist: str
    song_url: str
    thumbnail_url: str
    tags: str

    model_config = {"from_attributes": True}


class SongUploadResponse(BaseModel):
    message: str
    song: SongResponse


class FavouriteToggleResponse(BaseModel):
    message: bool
