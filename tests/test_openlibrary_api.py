from src.api.openlibrary_api import OpenLibraryApiClient


def test_openlibrary_falls_back_to_books_api_for_exact_isbn_classification():
    client = OpenLibraryApiClient()
    seen_urls = []

    def fake_request_json(url):
        seen_urls.append(url)
        if "/isbn/" in url:
            return {
                "key": "/books/OL22716386M",
                "isbn_10": ["0120147300"],
                "source_records": ["ia:advanceselectron88hawk"],
            }
        return {
            "ISBN:9780120147304": {
                "identifiers": {
                    "isbn_10": ["0120147300"],
                    "isbn_13": ["9780120147304"],
                },
                "classifications": {
                    "lc_classifications": ["TK7815 .A38eb vol. 88"],
                },
            }
        }

    client._request_json = fake_request_json

    payload = client.fetch("9780120147304")
    result = client.extract_call_numbers("9780120147304", payload)

    assert len(seen_urls) == 2
    assert "/isbn/9780120147304.json" in seen_urls[0]
    assert "bibkeys=ISBN%3A9780120147304" in seen_urls[1]
    assert result.status == "success"
    assert result.lccn == "TK7815 .A38eb vol. 88"
    assert result.isbns == ["0120147300", "9780120147304"]


def test_openlibrary_skips_books_api_when_edition_has_classification():
    client = OpenLibraryApiClient()
    seen_urls = []

    def fake_request_json(url):
        seen_urls.append(url)
        return {
            "isbn_13": ["9780000000001"],
            "lc_classifications": ["QA76.73.P98"],
        }

    client._request_json = fake_request_json

    payload = client.fetch("9780000000001")
    result = client.extract_call_numbers("9780000000001", payload)

    assert len(seen_urls) == 1
    assert result.status == "success"
    assert result.lccn == "QA76.73.P98"


def test_openlibrary_accepts_lc_classification_ranges_from_books_api():
    client = OpenLibraryApiClient()

    def fake_request_json(url):
        if "/isbn/" in url:
            return {"isbn_13": ["9780306480577"]}
        return {
            "ISBN:9780306480577": {
                "identifiers": {"isbn_13": ["9780306480577"]},
                "classifications": {"lc_classifications": ["QK710-899"]},
            }
        }

    client._request_json = fake_request_json

    payload = client.fetch("9780306480577")
    result = client.extract_call_numbers("9780306480577", payload)

    assert result.status == "success"
    assert result.lccn == "QK710-899"
