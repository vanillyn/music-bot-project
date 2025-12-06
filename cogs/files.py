import os
from typing import List, Tuple


class Files:
    def __init__(self) -> None:
        self.audio_dir: str = "audio_files"
        self.bg_music_dir: str = "background_music"
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.bg_music_dir, exist_ok=True)
        self.valid_extensions: Tuple[str, ...] = (".mp3", ".wav", ".ogg", ".m4a")

    def is_valid_audio(self, filename: str) -> bool:
        return filename.endswith(self.valid_extensions)

    def get_audio_path(self, filename: str) -> str:
        safe_name = os.path.basename(filename)
        return os.path.join(self.audio_dir, safe_name)

    def get_bg_music_path(self, filename: str) -> str:
        return os.path.join(self.bg_music_dir, filename)

    def file_exists(self, filepath: str) -> bool:
        return os.path.exists(filepath)

    def list_audio_files(self) -> List[str]:
        return [f for f in os.listdir(self.audio_dir) if self.is_valid_audio(f)]

    def list_bg_music_files(self) -> List[str]:
        return [f for f in os.listdir(self.bg_music_dir) if self.is_valid_audio(f)]
