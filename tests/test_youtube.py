"""Unit tests for youtube.py — no network calls, pure parsing logic."""

from yt2apple.youtube import Track, _parse_title, _parse_description_tracks


# ---------------------------------------------------------------------------
# Title parsing
# ---------------------------------------------------------------------------

def test_parse_title_artist_dash():
    track = _parse_title("아이유 - 밤편지")
    assert track.artist == "아이유"
    assert track.title == "밤편지"


def test_parse_title_strip_mv():
    track = _parse_title("BTS - Butter (Official MV)")
    assert track.title == "Butter"
    assert track.artist == "BTS"


def test_parse_title_no_artist():
    track = _parse_title("Bohemian Rhapsody")
    assert track.artist is None
    assert track.title == "Bohemian Rhapsody"


def test_parse_title_feat():
    track = _parse_title("Dynamite (feat. BTS)")
    assert track.title == "Dynamite"
    assert track.artist == "BTS"


def test_parse_title_strip_official_video():
    track = _parse_title("NewJeans - Hype Boy (Official Video)")
    assert track.title == "Hype Boy"
    assert track.artist == "NewJeans"


def test_parse_title_strip_lyric_video():
    track = _parse_title("aespa - Drama (Lyric Video)")
    assert track.title == "Drama"
    assert track.artist == "aespa"


def test_parse_title_korean_english_dupe_artist():
    # "아이유(IU) - 밤편지" → keep Korean artist
    track = _parse_title("아이유(IU) - 밤편지")
    assert track.artist == "아이유"
    assert track.title == "밤편지"


# ---------------------------------------------------------------------------
# Timestamp / description parsing
# ---------------------------------------------------------------------------

def test_parse_timestamp_lines():
    description = """\
Track list:
00:00 아이유 - 밤편지
3:42 BTS - Butter
1:07:15 NewJeans - Hype Boy
"""
    tracks = _parse_description_tracks(description)
    assert len(tracks) == 3
    assert tracks[0].artist == "아이유"
    assert tracks[0].title == "밤편지"
    assert tracks[1].artist == "BTS"
    assert tracks[1].title == "Butter"
    assert tracks[2].artist == "NewJeans"
    assert tracks[2].title == "Hype Boy"


def test_parse_numbered_list():
    description = """\
1. 아이유 - 밤편지
2. BTS - Butter
3. Bohemian Rhapsody
"""
    tracks = _parse_description_tracks(description)
    assert len(tracks) == 3
    assert tracks[0].artist == "아이유"
    assert tracks[0].title == "밤편지"
    assert tracks[1].artist == "BTS"
    assert tracks[1].title == "Butter"
    assert tracks[2].artist is None
    assert tracks[2].title == "Bohemian Rhapsody"


def test_parse_description_empty():
    tracks = _parse_description_tracks("")
    assert tracks == []


def test_parse_description_no_timestamps():
    description = "Just a random description with no song list."
    tracks = _parse_description_tracks(description)
    assert tracks == []


# ---------------------------------------------------------------------------
# Track.search_query
# ---------------------------------------------------------------------------

def test_search_query_with_artist():
    t = Track(title="밤편지", artist="아이유")
    assert t.search_query() == "아이유 밤편지"


def test_search_query_no_artist():
    t = Track(title="Bohemian Rhapsody")
    assert t.search_query() == "Bohemian Rhapsody"
