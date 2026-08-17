"""
Test Marketing Image Variants Feature - API Tests
Tests for:
1. POST /api/marketing/image - generates 3 image variants
2. POST /api/marketing/posts/{post_id}/image/select - selects a variant
3. Retrocompatibility with old posts (single image_url)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"


@pytest.fixture(scope="module")
def auth_session():
    """Login and return authenticated session"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return session


class TestMarketingImageVariantsAPI:
    """Tests for the marketing image variants feature"""

    def test_get_marketing_content_returns_posts_with_variant_fields(self, auth_session):
        """GET /api/marketing/content should return posts with image_variants and selected_image_index"""
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        # If content exists, check structure
        if data.get("content") and data["content"].get("content"):
            content = data["content"]["content"]
            posts = content.get("posts", [])
            
            # Each post should have the variant fields
            for post in posts:
                assert "image_variants" in post, f"Post {post.get('id')} missing image_variants"
                assert "selected_image_index" in post, f"Post {post.get('id')} missing selected_image_index"
                
                # If variants exist, selected_image_index should be valid
                variants = post.get("image_variants", [])
                selected = post.get("selected_image_index")
                if variants:
                    assert isinstance(selected, int), "selected_image_index should be int when variants exist"
                    assert 0 <= selected < len(variants), "selected_image_index out of range"
                    # image_url should match selected variant
                    assert post.get("image_url") == variants[selected], "image_url should match selected variant"
        
        print("PASS: Marketing content returns posts with variant fields")

    def test_generate_marketing_content_creates_posts_with_variant_structure(self, auth_session):
        """POST /api/marketing/generate should create posts with proper variant structure"""
        resp = auth_session.post(f"{BASE_URL}/api/marketing/generate")
        assert resp.status_code == 200
        data = resp.json()
        
        content = data.get("content", {}).get("content", {})
        posts = content.get("posts", [])
        
        assert len(posts) >= 10, "Should generate at least 10 posts"
        
        for post in posts:
            # New posts should have empty variants initially
            assert "image_variants" in post
            assert "selected_image_index" in post
            assert post.get("status") == "draft"
            
        print(f"PASS: Generated {len(posts)} posts with proper variant structure")

    def test_select_image_variant_updates_post(self, auth_session):
        """POST /api/marketing/posts/{post_id}/image/select should update selected_image_index"""
        # First get content to find a post with variants
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        if not data.get("content") or not data["content"].get("content"):
            pytest.skip("No marketing content available")
        
        content = data["content"]["content"]
        posts = content.get("posts", [])
        
        # Find a post with image variants
        post_with_variants = None
        for post in posts:
            variants = post.get("image_variants", [])
            if len(variants) >= 2:
                post_with_variants = post
                break
        
        if not post_with_variants:
            pytest.skip("No post with multiple variants found - need to generate images first")
        
        post_id = post_with_variants["id"]
        variants = post_with_variants["image_variants"]
        current_index = post_with_variants.get("selected_image_index", 0)
        
        # Select a different variant
        new_index = (current_index + 1) % len(variants)
        
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/posts/{post_id}/image/select",
            json={"variant_index": new_index}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("ok") is True
        assert data.get("selected_image_index") == new_index
        assert data.get("image_url") == variants[new_index]
        
        print(f"PASS: Selected variant {new_index} for post {post_id}")

    def test_select_invalid_variant_returns_error(self, auth_session):
        """POST /api/marketing/posts/{post_id}/image/select with invalid index should return 400"""
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        if not data.get("content") or not data["content"].get("content"):
            pytest.skip("No marketing content available")
        
        content = data["content"]["content"]
        posts = content.get("posts", [])
        
        # Find a post with variants
        post_with_variants = None
        for post in posts:
            variants = post.get("image_variants", [])
            if len(variants) >= 1:
                post_with_variants = post
                break
        
        if not post_with_variants:
            pytest.skip("No post with variants found")
        
        post_id = post_with_variants["id"]
        variants = post_with_variants["image_variants"]
        
        # Try to select an out-of-range index
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/posts/{post_id}/image/select",
            json={"variant_index": len(variants) + 10}
        )
        assert resp.status_code == 400
        
        print("PASS: Invalid variant index returns 400")

    def test_select_variant_on_post_without_images_returns_error(self, auth_session):
        """POST /api/marketing/posts/{post_id}/image/select on post without images should return 400"""
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        if not data.get("content") or not data["content"].get("content"):
            pytest.skip("No marketing content available")
        
        content = data["content"]["content"]
        posts = content.get("posts", [])
        
        # Find a post without variants
        post_without_variants = None
        for post in posts:
            variants = post.get("image_variants", [])
            if len(variants) == 0:
                post_without_variants = post
                break
        
        if not post_without_variants:
            pytest.skip("All posts have variants - cannot test this case")
        
        post_id = post_without_variants["id"]
        
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/posts/{post_id}/image/select",
            json={"variant_index": 0}
        )
        assert resp.status_code == 400
        
        print("PASS: Select variant on post without images returns 400")

    def test_post_status_workflow_preserves_image_variants(self, auth_session):
        """POST /api/marketing/posts/{post_id}/status should preserve image_variants"""
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        if not data.get("content") or not data["content"].get("content"):
            pytest.skip("No marketing content available")
        
        content = data["content"]["content"]
        posts = content.get("posts", [])
        
        # Find a draft post
        draft_post = None
        for post in posts:
            if post.get("status") == "draft":
                draft_post = post
                break
        
        if not draft_post:
            pytest.skip("No draft post found")
        
        post_id = draft_post["id"]
        original_variants = draft_post.get("image_variants", [])
        original_selected = draft_post.get("selected_image_index")
        
        # Approve the post
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/posts/{post_id}/status",
            json={"status": "approved"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Check that variants are preserved
        updated_post = data.get("post", {})
        assert updated_post.get("image_variants") == original_variants
        assert updated_post.get("selected_image_index") == original_selected
        assert updated_post.get("status") == "approved"
        
        # Reset back to draft
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/posts/{post_id}/status",
            json={"status": "draft"}
        )
        assert resp.status_code == 200
        
        print("PASS: Status workflow preserves image variants")

    def test_image_generation_endpoint_exists(self, auth_session):
        """POST /api/marketing/image endpoint should exist and accept index parameter"""
        # Just verify the endpoint exists and validates input
        # We won't actually generate images as it's slow and costs money
        
        # Test with invalid index
        resp = auth_session.post(
            f"{BASE_URL}/api/marketing/image",
            json={"index": -1}
        )
        # Should return 404 (post not found) not 500
        assert resp.status_code in [404, 400], f"Expected 404 or 400, got {resp.status_code}"
        
        print("PASS: Image generation endpoint exists and validates input")


class TestMarketingImageVariantsRetrocompat:
    """Tests for retrocompatibility with old posts"""

    def test_legacy_post_migration_on_content_fetch(self, auth_session):
        """Old posts with only image_url should get image_variants backfilled"""
        # This is tested by the unit tests, but we verify the API behavior
        resp = auth_session.get(f"{BASE_URL}/api/marketing/content")
        assert resp.status_code == 200
        data = resp.json()
        
        if not data.get("content") or not data["content"].get("content"):
            pytest.skip("No marketing content available")
        
        content = data["content"]["content"]
        posts = content.get("posts", [])
        
        # All posts should have the variant fields
        for post in posts:
            assert "image_variants" in post
            assert "selected_image_index" in post
            
            # If image_url exists, it should be in variants
            image_url = post.get("image_url")
            variants = post.get("image_variants", [])
            if image_url and variants:
                assert image_url in variants, "image_url should be in variants"
        
        print("PASS: All posts have variant fields (retrocompat)")
