#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test cases for the BloodHoundClient class.
"""

import base64
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from bhopengraph.BloodHoundClient import (
    BloodHoundAPIError,
    BloodHoundAuthError,
    BloodHoundClient,
    BloodHoundClientError,
)


class TestBloodHoundClientConstructor(unittest.TestCase):
    """Test BloodHoundClient initialization."""

    def test_init_stores_url_stripped(self):
        client = BloodHoundClient("https://example.com/", "tid", "mykey")
        self.assertEqual(client.base_url, "https://example.com")

    def test_init_stores_token_key(self):
        client = BloodHoundClient("https://example.com", "tid", "my-secret-key")
        self.assertEqual(client.token_key, "my-secret-key")

    def test_init_stores_token_id(self):
        client = BloodHoundClient("https://example.com", "my-token-id", "mykey")
        self.assertEqual(client.token_id, "my-token-id")


class TestBloodHoundClientSigning(unittest.TestCase):
    """Test HMAC signing logic."""

    def setUp(self):
        self.client = BloodHoundClient("https://bh.example.com", "token-123", "test-secret-key-1234")

    def test_sign_request_returns_three_headers(self):
        headers = self.client._sign_request("GET", "/api/v2/custom-nodes")
        self.assertIn("Authorization", headers)
        self.assertIn("RequestDate", headers)
        self.assertIn("Signature", headers)

    def test_sign_request_authorization_format(self):
        headers = self.client._sign_request("GET", "/api/v2/custom-nodes")
        self.assertEqual(headers["Authorization"], "bhesignature token-123")

    def test_sign_request_date_format(self):
        headers = self.client._sign_request("GET", "/api/v2/custom-nodes")
        # Should be RFC3339-ish: YYYY-MM-DDTHH:MM:SS.mmmZ
        date = headers["RequestDate"]
        self.assertTrue(date.endswith("Z"))
        self.assertIn("T", date)

    def test_sign_request_signature_is_base64(self):
        headers = self.client._sign_request("GET", "/api/v2/custom-nodes")
        sig = headers["Signature"]
        # Should decode without error
        decoded = base64.b64decode(sig)
        self.assertEqual(len(decoded), 32)  # SHA256 digest

    def test_sign_request_with_body_differs_from_without(self):
        headers_no_body = self.client._sign_request("POST", "/api/v2/custom-nodes")
        headers_with_body = self.client._sign_request("POST", "/api/v2/custom-nodes", b'{"name":"test"}')
        self.assertNotEqual(headers_no_body["Signature"], headers_with_body["Signature"])


class TestBloodHoundClientRequests(unittest.TestCase):
    """Test HTTP request methods with mocked urllib."""

    def setUp(self):
        self.client = BloodHoundClient("https://bh.example.com", "tid", "test-secret-key")

    def _mock_response(self, data, status=200):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode("utf-8")
        mock_resp.status = status
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_get_custom_nodes(self, mock_urlopen):
        expected = {"data": [{"name": "AWSUser"}]}
        mock_urlopen.return_value = self._mock_response(expected)
        result = self.client.get_custom_nodes()
        self.assertEqual(result, expected)

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_get_custom_node(self, mock_urlopen):
        expected = {"name": "AWSUser", "icon": {"type": "font-awesome"}}
        mock_urlopen.return_value = self._mock_response(expected)
        result = self.client.get_custom_node("AWSUser")
        self.assertEqual(result, expected)

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_create_custom_node(self, mock_urlopen):
        expected = {"name": "AWSUser"}
        mock_urlopen.return_value = self._mock_response(expected)
        icon = {"type": "font-awesome", "name": "user", "color": "#3B48CC"}
        result = self.client.create_custom_node("AWSUser", icon)
        self.assertEqual(result, expected)
        # Verify POST method
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_update_custom_node(self, mock_urlopen):
        expected = {"name": "AWSUser"}
        mock_urlopen.return_value = self._mock_response(expected)
        icon = {"type": "font-awesome", "name": "user", "color": "#3B48CC"}
        result = self.client.update_custom_node("AWSUser", icon)
        self.assertEqual(result, expected)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "PUT")

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_delete_custom_node(self, mock_urlopen):
        expected = {}
        mock_urlopen.return_value = self._mock_response(expected)
        result = self.client.delete_custom_node("AWSUser")
        self.assertEqual(result, expected)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "DELETE")

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_auth_error_on_401(self, mock_urlopen):
        from urllib.error import HTTPError
        error = HTTPError("url", 401, "Unauthorized", {}, MagicMock(read=MagicMock(return_value=b"unauthorized")))
        error.read = MagicMock(return_value=b"unauthorized")
        mock_urlopen.side_effect = error
        with self.assertRaises(BloodHoundAuthError):
            self.client.get_custom_nodes()

    @patch("bhopengraph.BloodHoundClient.urlopen")
    def test_api_error_on_500(self, mock_urlopen):
        from urllib.error import HTTPError
        error = HTTPError("url", 500, "Server Error", {}, MagicMock(read=MagicMock(return_value=b"error")))
        error.read = MagicMock(return_value=b"error")
        mock_urlopen.side_effect = error
        with self.assertRaises(BloodHoundAPIError) as ctx:
            self.client.get_custom_nodes()
        self.assertEqual(ctx.exception.status_code, 500)


class TestBloodHoundClientUpload(unittest.TestCase):
    """Test bulk upload logic."""

    def setUp(self):
        self.client = BloodHoundClient("https://bh.example.com", "tid", "test-secret-key")

    @patch.object(BloodHoundClient, "update_custom_node")
    def test_upload_icons_updates_existing(self, mock_update):
        mock_update.return_value = {"name": "AWSUser"}
        config = {"custom_nodes": [{"kindName": "AWSUser", "config": {"icon": {"type": "font-awesome", "name": "user", "color": "#3B48CC"}}}]}
        results = self.client.upload_icons(config)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["action"], "updated")

    @patch.object(BloodHoundClient, "create_custom_node")
    @patch.object(BloodHoundClient, "update_custom_node")
    def test_upload_icons_creates_on_404(self, mock_update, mock_create):
        mock_update.side_effect = BloodHoundAPIError("Not found", status_code=404, response_body="")
        mock_create.return_value = {"name": "AWSUser"}
        config = {"custom_nodes": [{"kindName": "AWSUser", "config": {"icon": {"type": "font-awesome", "name": "user", "color": "#3B48CC"}}}]}
        results = self.client.upload_icons(config)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["action"], "created")

    @patch.object(BloodHoundClient, "update_custom_node")
    def test_upload_icons_raises_on_non_404_error(self, mock_update):
        mock_update.side_effect = BloodHoundAPIError("Server error", status_code=500, response_body="")
        config = {"custom_nodes": [{"kindName": "AWSUser", "config": {"icon": {"type": "font-awesome", "name": "user"}}}]}
        with self.assertRaises(BloodHoundAPIError):
            self.client.upload_icons(config)


class TestBloodHoundClientFileLoading(unittest.TestCase):
    """Test file loading methods."""

    def test_load_icons_from_file(self):
        data = {"custom_nodes": [{"kindName": "Test", "config": {"icon": {"type": "font-awesome", "name": "star"}}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            filepath = f.name
        try:
            result = BloodHoundClient.load_icons_from_file(filepath)
            self.assertEqual(result, data)
        finally:
            os.unlink(filepath)

    @patch.object(BloodHoundClient, "upload_icons")
    def test_upload_icons_from_file(self, mock_upload):
        mock_upload.return_value = [{"kind": "Test", "action": "created"}]
        data = {"custom_nodes": [{"kindName": "Test", "config": {"icon": {"type": "font-awesome", "name": "star"}}}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            filepath = f.name
        try:
            client = BloodHoundClient("https://bh.example.com", "tid", "testkey")
            result = client.upload_icons_from_file(filepath)
            self.assertEqual(len(result), 1)
            mock_upload.assert_called_once_with(data)
        finally:
            os.unlink(filepath)


class TestBloodHoundClientRepr(unittest.TestCase):
    """Test string representation."""

    def test_repr(self):
        client = BloodHoundClient("https://bh.example.com", "tid", "testkey")
        r = repr(client)
        self.assertIn("BloodHoundClient", r)
        self.assertIn("bh.example.com", r)
        self.assertIn("tid", r)


class TestExceptionHierarchy(unittest.TestCase):
    """Test exception class hierarchy."""

    def test_auth_error_is_client_error(self):
        self.assertTrue(issubclass(BloodHoundAuthError, BloodHoundClientError))

    def test_api_error_is_client_error(self):
        self.assertTrue(issubclass(BloodHoundAPIError, BloodHoundClientError))

    def test_api_error_stores_attributes(self):
        err = BloodHoundAPIError("msg", status_code=400, response_body="bad request")
        self.assertEqual(err.status_code, 400)
        self.assertEqual(err.response_body, "bad request")


if __name__ == "__main__":
    unittest.main()
