from tests.test_channel_project_api import client
from scripts.project_manifest import ProjectManifest


def test_nested_project_list_and_read_update(client):
    ProjectManifest.save("second/origin", channel_id="second", custom_script="Original")
    listing = client.get("/api/projects", headers={"X-OmniCut-Channel": "second"}).json()
    assert [row["project_name"] for row in listing["projects"]] == ["second/origin"]
    endpoint = "/api/channel-projects/second/origin"
    assert client.get(endpoint).status_code == 404
    response = client.get(endpoint, headers={"X-OmniCut-Channel": "second"})
    assert response.status_code == 200, response.text
    assert response.json()["custom_script"] == "Original"
    assert client.get(endpoint + "/snapshots", headers={"X-OmniCut-Channel": "second"}).status_code == 200
    response = client.patch(endpoint + "/state", headers={"X-OmniCut-Channel": "second"},
                            json={"hook_label": "Updated"})
    assert response.status_code == 200
    assert ProjectManifest.load("second/origin")["hook_label"] == "Updated"
