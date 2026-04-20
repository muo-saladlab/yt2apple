from unittest.mock import MagicMock, patch

from yt2apple.apple_music import create_playlist, search_song

DEV_TOKEN = "dev_token"
USER_TOKEN = "user_token"


def _make_search_response(song_ids: list[str]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": {
            "songs": {
                "data": [{"id": sid} for sid in song_ids]
            }
        }
    }
    return resp


def _make_empty_search_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": {"songs": {"data": []}}}
    return resp


class TestSearchSong:
    def test_search_song_with_artist(self):
        """artist+title query returns song id."""
        with patch("yt2apple.apple_music.requests.get") as mock_get:
            mock_get.return_value = _make_search_response(["123"])

            result = search_song("Bohemian Rhapsody", "Queen", DEV_TOKEN, USER_TOKEN)

        assert result == "123"
        # Should have been called once (artist+title succeeded on first try)
        mock_get.assert_called_once()
        call_params = mock_get.call_args[1]["params"]
        assert "Queen Bohemian Rhapsody" in call_params["term"]

    def test_search_song_fallback_to_title(self):
        """First query (artist+title) returns empty; second (title-only) returns a hit."""
        with patch("yt2apple.apple_music.requests.get") as mock_get:
            mock_get.side_effect = [
                _make_empty_search_response(),
                _make_search_response(["456"]),
            ]

            result = search_song("Bohemian Rhapsody", "Queen", DEV_TOKEN, USER_TOKEN)

        assert result == "456"
        assert mock_get.call_count == 2
        # Second call should use title only
        second_params = mock_get.call_args_list[1][1]["params"]
        assert second_params["term"] == "Bohemian Rhapsody"

    def test_search_song_not_found(self):
        """Both queries return empty; result is None."""
        with patch("yt2apple.apple_music.requests.get") as mock_get:
            mock_get.return_value = _make_empty_search_response()

            result = search_song("NoSuchSong", "NoSuchArtist", DEV_TOKEN, USER_TOKEN)

        assert result is None
        assert mock_get.call_count == 2


class TestCreatePlaylist:
    def test_create_playlist_success(self):
        """POST returns 201 with playlist data; playlist ID is returned."""
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {"data": [{"id": "p-789"}]}

        with patch("yt2apple.apple_music.requests.post", return_value=resp) as mock_post:
            result = create_playlist("My Playlist", ["123", "456"], DEV_TOKEN, USER_TOKEN)

        assert result == "p-789"
        mock_post.assert_called_once()
        call_json = mock_post.call_args[1]["json"]
        assert call_json["attributes"]["name"] == "My Playlist"
        tracks = call_json["relationships"]["tracks"]["data"]
        assert len(tracks) == 2
        assert tracks[0] == {"id": "123", "type": "songs"}
        assert tracks[1] == {"id": "456", "type": "songs"}

    def test_create_playlist_failure(self):
        """POST returns 401; result is None."""
        resp = MagicMock()
        resp.status_code = 401

        with patch("yt2apple.apple_music.requests.post", return_value=resp):
            result = create_playlist("My Playlist", ["123"], DEV_TOKEN, USER_TOKEN)

        assert result is None
