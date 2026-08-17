"""
Backend Testing for New Image Flow - Marketing Module
Tests the new image variant endpoints for backward compatibility and functionality
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com"
CREDENTIALS = {
    "email": "adminceoai@gmail.com",
    "password": "12345"
}

class TestImageFlow:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []
        
    def log(self, test_name, passed, message, details=None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"\n{status}: {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
        return passed
    
    def login(self):
        """Authenticate and get session"""
        print("\n" + "="*80)
        print("AUTHENTICATING...")
        print("="*80)
        
        url = f"{BASE_URL}/api/auth/login"
        response = self.session.post(url, json=CREDENTIALS)
        
        if response.status_code == 200:
            data = response.json()
            user = data.get("user", {})
            self.log(
                "Authentication",
                True,
                f"Login successful as {user.get('email')} (role: {user.get('role')})",
                {"user": user}
            )
            return True
        else:
            self.log(
                "Authentication",
                False,
                f"Login failed with status {response.status_code}",
                {"response": response.text}
            )
            return False
    
    def test_get_marketing_content(self):
        """Test GET /api/marketing/content - validate posts with image_variants and selected_image_index"""
        print("\n" + "="*80)
        print("TEST 1: GET /api/marketing/content")
        print("="*80)
        
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "GET /api/marketing/content",
                False,
                f"Request failed with status {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        content = data.get("content", {})
        posts = content.get("content", {}).get("posts", [])
        
        if not posts:
            return self.log(
                "GET /api/marketing/content",
                False,
                "No posts found in content",
                {"content_keys": list(content.keys())}
            )
        
        # Check for posts with images
        posts_with_images = []
        posts_without_images = []
        
        for i, post in enumerate(posts):
            post_id = post.get("id")
            image_variants = post.get("image_variants", [])
            selected_image_index = post.get("selected_image_index")
            image_url = post.get("image_url")
            
            if image_variants:
                posts_with_images.append({
                    "index": i,
                    "id": post_id,
                    "title": post.get("titulo", "")[:50],
                    "image_variants_count": len(image_variants),
                    "selected_image_index": selected_image_index,
                    "image_url": image_url[:80] if image_url else None,
                    "variants_sample": [v[:80] for v in image_variants[:2]]
                })
            else:
                posts_without_images.append({
                    "index": i,
                    "id": post_id,
                    "title": post.get("titulo", "")[:50]
                })
        
        # Validate coherence for posts with images
        coherence_issues = []
        for post_info in posts_with_images:
            idx = post_info["selected_image_index"]
            variants_count = post_info["image_variants_count"]
            
            # Check if selected_image_index is valid
            if idx is None:
                coherence_issues.append(f"Post {post_info['id']}: selected_image_index is None but has {variants_count} variants")
            elif not isinstance(idx, int):
                coherence_issues.append(f"Post {post_info['id']}: selected_image_index is not an integer ({type(idx).__name__})")
            elif idx < 0 or idx >= variants_count:
                coherence_issues.append(f"Post {post_info['id']}: selected_image_index ({idx}) out of range [0, {variants_count-1}]")
        
        summary = {
            "total_posts": len(posts),
            "posts_with_images": len(posts_with_images),
            "posts_without_images": len(posts_without_images),
            "sample_posts_with_images": posts_with_images[:3],
            "sample_posts_without_images": posts_without_images[:3],
            "coherence_issues": coherence_issues
        }
        
        passed = response.status_code == 200 and len(coherence_issues) == 0
        
        return self.log(
            "GET /api/marketing/content",
            passed,
            f"Found {len(posts)} posts: {len(posts_with_images)} with images, {len(posts_without_images)} without. Coherence: {'OK' if not coherence_issues else 'ISSUES FOUND'}",
            summary
        )
    
    def test_post_marketing_image(self):
        """Test POST /api/marketing/image - generate 3 image variants"""
        print("\n" + "="*80)
        print("TEST 2: POST /api/marketing/image")
        print("="*80)
        
        # First get a post without images
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "POST /api/marketing/image - Get Content",
                False,
                f"Failed to get content: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        posts = data.get("content", {}).get("content", {}).get("posts", [])
        
        # Find a post without images or with images (to test regeneration)
        test_post_index = None
        test_post_id = None
        had_images_before = False
        
        for i, post in enumerate(posts):
            if not post.get("image_variants"):
                test_post_index = i
                test_post_id = post.get("id")
                had_images_before = False
                break
        
        # If no post without images, use the first post with images to test regeneration
        if test_post_index is None and posts:
            test_post_index = 0
            test_post_id = posts[0].get("id")
            had_images_before = True
        
        if test_post_index is None:
            return self.log(
                "POST /api/marketing/image",
                False,
                "No posts available for testing",
                None
            )
        
        print(f"\nTesting with post index {test_post_index} (id: {test_post_id})")
        print(f"Post had images before: {had_images_before}")
        
        # Generate images
        url = f"{BASE_URL}/api/marketing/image"
        payload = {"index": test_post_index}
        response = self.session.post(url, json=payload)
        
        if response.status_code != 200:
            return self.log(
                "POST /api/marketing/image",
                False,
                f"Request failed with status {response.status_code}",
                {"payload": payload, "response": response.text[:500]}
            )
        
        result = response.json()
        image_variants = result.get("image_variants", [])
        selected_image_index = result.get("selected_image_index")
        image_url = result.get("image_url")
        
        # Validate response
        issues = []
        
        if not isinstance(image_variants, list):
            issues.append(f"image_variants is not a list: {type(image_variants).__name__}")
        elif len(image_variants) != 3:
            issues.append(f"Expected 3 image variants, got {len(image_variants)}")
        
        if selected_image_index != 0:
            issues.append(f"Expected selected_image_index=0, got {selected_image_index}")
        
        if not image_url:
            issues.append("image_url is empty")
        elif image_variants and image_url != image_variants[0]:
            issues.append(f"image_url does not match first variant")
        
        passed = response.status_code == 200 and len(issues) == 0
        
        return self.log(
            "POST /api/marketing/image",
            passed,
            f"Generated {len(image_variants)} variants, selected_image_index={selected_image_index}. Issues: {len(issues)}",
            {
                "test_post_index": test_post_index,
                "test_post_id": test_post_id,
                "had_images_before": had_images_before,
                "image_variants_count": len(image_variants),
                "selected_image_index": selected_image_index,
                "image_url_sample": image_url[:80] if image_url else None,
                "variants_sample": [v[:80] for v in image_variants] if image_variants else [],
                "issues": issues
            }
        )
    
    def test_post_image_select(self):
        """Test POST /api/marketing/posts/{post_id}/image/select - select a variant"""
        print("\n" + "="*80)
        print("TEST 3: POST /api/marketing/posts/{post_id}/image/select")
        print("="*80)
        
        # First get a post with images
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "POST /api/marketing/posts/{post_id}/image/select - Get Content",
                False,
                f"Failed to get content: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        posts = data.get("content", {}).get("content", {}).get("posts", [])
        
        # Find a post with images
        test_post = None
        for post in posts:
            if post.get("image_variants") and len(post.get("image_variants", [])) >= 2:
                test_post = post
                break
        
        if not test_post:
            return self.log(
                "POST /api/marketing/posts/{post_id}/image/select",
                False,
                "No posts with multiple image variants found for testing",
                None
            )
        
        post_id = test_post.get("id")
        variants = test_post.get("image_variants", [])
        current_index = test_post.get("selected_image_index", 0)
        
        # Select a different variant (if current is 0, select 1; otherwise select 0)
        new_index = 1 if current_index == 0 else 0
        
        print(f"\nTesting with post_id: {post_id}")
        print(f"Current selected_image_index: {current_index}")
        print(f"Selecting variant_index: {new_index}")
        print(f"Total variants: {len(variants)}")
        
        # Select variant
        url = f"{BASE_URL}/api/marketing/posts/{post_id}/image/select"
        payload = {"variant_index": new_index}
        response = self.session.post(url, json=payload)
        
        if response.status_code != 200:
            return self.log(
                "POST /api/marketing/posts/{post_id}/image/select",
                False,
                f"Request failed with status {response.status_code}",
                {"payload": payload, "response": response.text[:500]}
            )
        
        result = response.json()
        
        # Validate response
        issues = []
        
        if not result.get("ok"):
            issues.append("Response ok field is not True")
        
        if result.get("post_id") != post_id:
            issues.append(f"post_id mismatch: expected {post_id}, got {result.get('post_id')}")
        
        if result.get("selected_image_index") != new_index:
            issues.append(f"selected_image_index not updated: expected {new_index}, got {result.get('selected_image_index')}")
        
        expected_url = variants[new_index] if new_index < len(variants) else None
        if result.get("image_url") != expected_url:
            issues.append(f"image_url not updated correctly")
        
        # Verify persistence by fetching content again
        url = f"{BASE_URL}/api/marketing/content"
        response2 = self.session.get(url)
        
        if response2.status_code == 200:
            data2 = response2.json()
            posts2 = data2.get("content", {}).get("content", {}).get("posts", [])
            updated_post = next((p for p in posts2 if p.get("id") == post_id), None)
            
            if updated_post:
                persisted_index = updated_post.get("selected_image_index")
                persisted_url = updated_post.get("image_url")
                
                if persisted_index != new_index:
                    issues.append(f"selected_image_index not persisted: expected {new_index}, got {persisted_index}")
                
                if persisted_url != expected_url:
                    issues.append(f"image_url not persisted correctly")
            else:
                issues.append("Could not find post after update to verify persistence")
        
        passed = response.status_code == 200 and len(issues) == 0
        
        return self.log(
            "POST /api/marketing/posts/{post_id}/image/select",
            passed,
            f"Selected variant {new_index}, updated selected_image_index and image_url. Issues: {len(issues)}",
            {
                "post_id": post_id,
                "previous_index": current_index,
                "new_index": new_index,
                "selected_image_index": result.get("selected_image_index"),
                "image_url_sample": result.get("image_url", "")[:80],
                "issues": issues
            }
        )
    
    def test_backward_compatibility(self):
        """Test backward compatibility - existing posts should work correctly"""
        print("\n" + "="*80)
        print("TEST 4: Backward Compatibility")
        print("="*80)
        
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "Backward Compatibility",
                False,
                f"Failed to get content: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        posts = data.get("content", {}).get("content", {}).get("posts", [])
        
        # Check all posts for backward compatibility
        compatibility_issues = []
        posts_analyzed = 0
        
        for post in posts:
            posts_analyzed += 1
            post_id = post.get("id")
            
            # Check required fields exist
            if "id" not in post:
                compatibility_issues.append(f"Post missing 'id' field")
                continue
            
            # Check image fields
            image_variants = post.get("image_variants")
            selected_image_index = post.get("selected_image_index")
            image_url = post.get("image_url")
            
            # If post has image_variants, validate structure
            if image_variants is not None:
                if not isinstance(image_variants, list):
                    compatibility_issues.append(f"Post {post_id}: image_variants is not a list")
                elif len(image_variants) > 0:
                    # If has variants, should have selected_image_index
                    if selected_image_index is None:
                        compatibility_issues.append(f"Post {post_id}: has image_variants but selected_image_index is None")
                    elif not isinstance(selected_image_index, int):
                        compatibility_issues.append(f"Post {post_id}: selected_image_index is not an integer")
                    elif selected_image_index < 0 or selected_image_index >= len(image_variants):
                        compatibility_issues.append(f"Post {post_id}: selected_image_index out of range")
                    
                    # If has variants and selected_image_index, image_url should match
                    if isinstance(selected_image_index, int) and 0 <= selected_image_index < len(image_variants):
                        expected_url = image_variants[selected_image_index]
                        if image_url != expected_url:
                            compatibility_issues.append(f"Post {post_id}: image_url does not match selected variant")
            
            # Check other essential fields are not broken
            essential_fields = ["titulo", "tema", "formato", "status"]
            for field in essential_fields:
                if field not in post:
                    compatibility_issues.append(f"Post {post_id}: missing essential field '{field}'")
        
        passed = len(compatibility_issues) == 0
        
        return self.log(
            "Backward Compatibility",
            passed,
            f"Analyzed {posts_analyzed} posts. Compatibility issues: {len(compatibility_issues)}",
            {
                "posts_analyzed": posts_analyzed,
                "compatibility_issues": compatibility_issues[:10],  # Show first 10 issues
                "total_issues": len(compatibility_issues)
            }
        )
    
    def test_payload_integrity(self):
        """Test that image operations don't break other post fields"""
        print("\n" + "="*80)
        print("TEST 5: Payload Integrity")
        print("="*80)
        
        # Get initial state
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "Payload Integrity - Get Initial State",
                False,
                f"Failed to get content: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        posts = data.get("content", {}).get("content", {}).get("posts", [])
        
        if not posts:
            return self.log(
                "Payload Integrity",
                False,
                "No posts available for testing",
                None
            )
        
        # Find a post with images to test selection
        test_post = None
        for post in posts:
            if post.get("image_variants") and len(post.get("image_variants", [])) >= 2:
                test_post = post
                break
        
        if not test_post:
            return self.log(
                "Payload Integrity",
                False,
                "No posts with multiple variants found for testing",
                None
            )
        
        post_id = test_post.get("id")
        
        # Capture initial state of non-image fields
        initial_state = {
            "titulo": test_post.get("titulo"),
            "tema": test_post.get("tema"),
            "formato": test_post.get("formato"),
            "status": test_post.get("status"),
            "copy": test_post.get("copy"),
            "hashtags": test_post.get("hashtags"),
        }
        
        # Perform image selection
        current_index = test_post.get("selected_image_index", 0)
        new_index = 1 if current_index == 0 else 0
        
        url = f"{BASE_URL}/api/marketing/posts/{post_id}/image/select"
        payload = {"variant_index": new_index}
        response = self.session.post(url, json=payload)
        
        if response.status_code != 200:
            return self.log(
                "Payload Integrity - Image Selection",
                False,
                f"Image selection failed: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        # Get updated state
        url = f"{BASE_URL}/api/marketing/content"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return self.log(
                "Payload Integrity - Get Updated State",
                False,
                f"Failed to get updated content: {response.status_code}",
                {"response": response.text[:500]}
            )
        
        data = response.json()
        posts = data.get("content", {}).get("content", {}).get("posts", [])
        updated_post = next((p for p in posts if p.get("id") == post_id), None)
        
        if not updated_post:
            return self.log(
                "Payload Integrity",
                False,
                "Could not find post after update",
                None
            )
        
        # Compare non-image fields
        integrity_issues = []
        
        for field, initial_value in initial_state.items():
            updated_value = updated_post.get(field)
            if updated_value != initial_value:
                integrity_issues.append(f"Field '{field}' changed: '{initial_value}' -> '{updated_value}'")
        
        passed = len(integrity_issues) == 0
        
        return self.log(
            "Payload Integrity",
            passed,
            f"Image selection did not break other fields. Issues: {len(integrity_issues)}",
            {
                "post_id": post_id,
                "fields_checked": list(initial_state.keys()),
                "integrity_issues": integrity_issues
            }
        )
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("BACKEND TESTING: NEW IMAGE FLOW - MARKETING MODULE")
        print("="*80)
        print(f"Base URL: {BASE_URL}")
        print(f"Credentials: {CREDENTIALS['email']}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Authenticate
        if not self.login():
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Run tests
        test_methods = [
            self.test_get_marketing_content,
            self.test_post_marketing_image,
            self.test_post_image_select,
            self.test_backward_compatibility,
            self.test_payload_integrity,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log(
                    test_method.__name__,
                    False,
                    f"Test raised exception: {str(e)}",
                    {"exception": str(e)}
                )
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if "✅ PASS" in r["status"])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print("\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80)
        
        for result in self.test_results:
            print(f"\n{result['status']}: {result['test']}")
            print(f"   {result['message']}")
        
        return failed_tests == 0


if __name__ == "__main__":
    tester = TestImageFlow()
    success = tester.run_all_tests()
    
    print("\n" + "="*80)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)
    
    exit(0 if success else 1)
