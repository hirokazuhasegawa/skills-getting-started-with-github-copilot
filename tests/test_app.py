import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """
    Fixture providing a TestClient instance for testing.
    Each test gets a fresh client instance.
    """
    return TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_200(self, client):
        # Arrange
        # (client fixture provides the test client)

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_get_activities_contains_all_required_fields(self, client):
        # Arrange
        required_fields = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        for activity_name, activity_data in activities.items():
            assert all(field in activity_data for field in required_fields)
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email in client.get("/activities").json()[activity_name]["participants"]

    def test_signup_duplicate_email_returns_400(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity_returns_404(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "test@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_signup_with_special_characters_in_email(self, client):
        # Arrange
        activity_name = "Programming Class"
        email = "student+test@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert email in client.get("/activities").json()[activity_name]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_success(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )

        # Assert
        assert response.status_code == 200
        assert email not in client.get("/activities").json()[activity_name]["participants"]

    def test_remove_nonregistered_participant_returns_400(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )

        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_remove_from_nonexistent_activity_returns_404(self, client):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "test@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_remove_participant_then_readd(self, client):
        # Arrange
        activity_name = "Programming Class"
        email = "emma@mergington.edu"  # Already signed up

        # Act - Remove
        response_delete = client.delete(
            f"/activities/{activity_name}/participants/{email}"
        )

        # Act - Re-add
        response_readd = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response_delete.status_code == 200
        assert response_readd.status_code == 200
        assert email in client.get("/activities").json()[activity_name]["participants"]


class TestRedirect:
    """Tests for GET / endpoint"""

    def test_root_redirects_to_static(self, client):
        # Arrange
        # (client fixture provides the test client)

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code in [301, 302, 303, 307, 308]  # Redirect status codes
        assert "/static/index.html" in response.headers["location"]


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_signup_with_empty_email_parameter(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = ""

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert - Should handle empty email (may succeed or fail based on app logic)
        assert response.status_code in [200, 400, 422]

    def test_signup_multiple_participants_different_emails(self, client):
        # Arrange
        activity_name = "Art Club"
        emails = ["artist1@mergington.edu", "artist2@mergington.edu", "artist3@mergington.edu"]

        # Act
        responses = [
            client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            for email in emails
        ]

        # Assert
        assert all(resp.status_code == 200 for resp in responses)
        participants = client.get("/activities").json()[activity_name]["participants"]
        assert all(email in participants for email in emails)

    def test_activity_name_case_sensitivity(self, client):
        # Arrange
        activity_name_lower = "chess club"
        email = "test@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name_lower}/signup",
            params={"email": email}
        )

        # Assert - Should not find activity with different case
        assert response.status_code == 404
