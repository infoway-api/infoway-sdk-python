import httpx
import pytest
import respx

from infoway._http import HttpClient
from infoway.rest.packages import PackageClient


@pytest.fixture
def packages():
    return PackageClient(HttpClient(api_key="test-key", max_retries=1))


@respx.mock
def test_get_info(packages):
    route = respx.get("https://data.infoway.io/package/info").mock(
        return_value=httpx.Response(
            200,
            json={"ret": 200, "msg": "ok", "data": {"packageName": "Professional"}},
        )
    )
    result = packages.get_info()
    assert route.calls[0].request.url.path == "/package/info"
    assert result["packageName"] == "Professional"
