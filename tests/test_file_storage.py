import asyncio
import hashlib
import tempfile
import unittest
from pathlib import Path

from infrastructure.storage.file_storage import FileStorage


class FakeUpload:
    filename = "../unsafe/name.wav"
    content_type = "audio/wav"

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    async def read(self, size: int) -> bytes:
        chunk = self.data[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class FileStorageTests(unittest.TestCase):
    def test_upload_is_streamed_to_user_scoped_storage(self):
        data = b"voice-data"
        with tempfile.TemporaryDirectory() as directory:
            storage = FileStorage(Path(directory))
            stored = asyncio.run(storage.save_upload(FakeUpload(data), user_id="user-1", asset_id="asset-1"))

            self.assertTrue(stored.path.exists())
            self.assertEqual(stored.kind, "audio")
            self.assertEqual(stored.size_bytes, len(data))
            self.assertEqual(stored.sha256, hashlib.sha256(data).hexdigest())
            self.assertEqual(stored.path.parent.name, "assets")
            self.assertNotIn("unsafe", stored.path.name)


if __name__ == "__main__":
    unittest.main()
