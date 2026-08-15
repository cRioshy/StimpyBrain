from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

@dataclass(frozen=True)
class PublicSocialPost:
    platform:str;account_id:str;account_handle:str;account_display_name:str;post_id:str;text:str;published_at:datetime;language:str="und";engagement:dict|None=None
class ReadOnlySocialAdapter(Protocol):
    def read_public_posts(self,handle:str,since_id:str|None=None,limit:int=25)->tuple[PublicSocialPost,...]: ...
