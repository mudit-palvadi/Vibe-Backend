from pydantic import BaseModel, Field


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


class UploadPart(BaseModel):
    key: str
    url: str
    headers: dict[str, str]


class UploadInitRequest(BaseModel):
    song_name: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)
    tags: str = ""
    audio_filename: str = "audio"
    thumbnail_filename: str = "thumbnail"


class UploadInitResponse(BaseModel):
    song_id: str
    audio: UploadPart
    thumbnail: UploadPart
    expires_in: int
