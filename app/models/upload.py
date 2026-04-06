from pydantic import BaseModel
from pydantic import Field
from typing import Optional
from fastapi import UploadFile
from pydantic import field_validator

class UploadRequest(BaseModel):
  # file can be null
  file: Optional[UploadFile] = Field(default=None, description="The file to upload")
  website_url: Optional[str] = Field(default=None, description="The URL of the website to upload")
  text: Optional[str] = Field(default=None, description="The text to upload")
  database_url: Optional[str] = Field(default=None, description="The URL of the database to upload")

  """
  Either file, website_url, text, or database_url must be provided.
  If multiple are provided, the file will be used.
  If no file is provided, the website_url, text, or database_url will be used.
  If no website_url, text, or database_url is provided, an error will be returned.
  """
  @field_validator("file", "website_url", "text", "database_url")
  def validate_required_fields(cls, v, values):
    if v is None and all(values.values()):
      raise ValueError("Either file, website_url, text, or database_url must be provided")
    return v