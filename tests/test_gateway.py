"""Tests for the model gateway (M3, issues #69, #70, #80).

Providers are tested with a mocked ``post_json`` so CI never needs live
provider credentials (docs/testing.md).
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from chad.gateway import (
    AnthropicProvider,
    FakeProvider,
    Gateway,
    GoogleProvider,
    LapisLLMProvider,
    OpenAIProvider,
)
from chad.gateway.capabilities import Capabilities, capabilities_for
from chad.gateway.errors import AuthError, GatewayError, InvalidRequestError
from chad.gateway.provider_contract import ModelResponse
from chad.runtime.contracts import Role


class FakeProviderTests(unittest.TestCase):
    def test_returns_scripted_responses(self):
        provider = FakeProvider(
            responses=[ModelResponse(content="one"), ModelResponse(content="two")]
        )
        self.assertEqual(provider.request("m", (), ()).content, "one")
        self.assertEqual(provider.request("m", (), ()).content, "two")
        self.assertEqual(provider.request("m", (), ()).content, "ok")
        self.assertTrue(provider.capabilities_for("m").tool_calling)

    def test_raises_configured_error(self):
        provider = FakeProvider(error=AuthError("bad key"))
        with self.assertRaises(AuthError):
            provider.request("m", (), ())


class RegistryTests(unittest.TestCase):
    def test_routes_providers(self):
        gw = Gateway()
        self.assertFalse(gw.has("fake"))
        gw.register(FakeProvider())
        self.assertTrue(gw.has("fake"))
        caps = gw.capabilities("fake", "m")
        self.assertIsInstance(caps, Capabilities)
        self.assertEqual(caps.provider, "fake")
        resp = gw.request("fake", "m", (), ())
        self.assertIsInstance(resp, ModelResponse)
        self.assertEqual(gw.providers(), ("fake",))

    def test_unknown_provider_errors(self):
        gw = Gateway()
        with self.assertRaises(GatewayError):
            gw.request("nope", "m", (), ())


class CapabilitiesTests(unittest.TestCase):
    def test_unknown_defaults(self):
        caps = capabilities_for("nope-provider", "nope-model")
        self.assertFalse(caps.streaming)
        self.assertFalse(caps.tool_calling)
        self.assertIsNone(caps.context_limit)


def _msg(role: str, content: str) -> object:
    from chad.runtime.contracts import Message

    return Message(role=Role(role), content=content)


class OpenAITests(unittest.TestCase):
    @patch("chad.gateway.openai.post_json")
    def test_mocked(self, mock_post):
        mock_post.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "hello",
                        "tool_calls": [
                            {
                                "id": "tc-1",
                                "function": {
                                    "name": "read",
                                    "arguments": '{"path": "a.txt"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        provider = OpenAIProvider(api_key="sk-test")
        resp = provider.request("gpt-4", (_msg("user", "read a.txt"),), ())
        self.assertEqual(resp.content, "hello")
        self.assertEqual(resp.tool_calls[0].name, "read")
        self.assertEqual(resp.tool_calls[0].arguments, {"path": "a.txt"})
        args, _ = mock_post.call_args
        self.assertEqual(args[0], "openai")
        self.assertEqual(args[2]["Authorization"], "Bearer sk-test")
        self.assertFalse(args[3]["stream"])

    @patch("chad.gateway.openai.post_json")
    def test_missing_api_key(self, mock_post):
        provider = OpenAIProvider(api_key=None)
        with self.assertRaises(GatewayError):
            provider.request("m", (), ())
        mock_post.assert_not_called()


class LapisTests(unittest.TestCase):
    @patch("chad.gateway.lapis.post_json")
    def test_mocked(self, mock_post):
        mock_post.return_value = {"choices": [{"message": {"content": "lapis reply"}}]}
        provider = LapisLLMProvider(api_key="sk-test")
        resp = provider.request("lapis-1", (_msg("user", "hi"),), ())
        self.assertEqual(resp.content, "lapis reply")
        args, _ = mock_post.call_args
        self.assertEqual(args[0], "lapisllm")
        self.assertEqual(args[2]["Authorization"], "Bearer sk-test")

    @patch("chad.gateway.lapis.post_json")
    def test_missing_api_key(self, mock_post):
        provider = LapisLLMProvider(api_key=None)
        with self.assertRaises(GatewayError):
            provider.request("m", (), ())
        mock_post.assert_not_called()


class AnthropicTests(unittest.TestCase):
    @patch("chad.gateway.anthropic.post_json")
    def test_mocked(self, mock_post):
        mock_post.return_value = {
            "content": [
                {"type": "text", "text": "claude says hi"},
                {
                    "type": "tool_use",
                    "id": "tu-1",
                    "name": "read",
                    "input": {"path": "b.txt"},
                },
            ]
        }
        provider = AnthropicProvider(api_key="sk-ant")
        resp = provider.request("claude-3", (_msg("user", "read b.txt"),), ())
        self.assertIn("claude says hi", resp.content)
        self.assertEqual(resp.tool_calls[0].name, "read")
        self.assertEqual(resp.tool_calls[0].arguments, {"path": "b.txt"})
        args, _ = mock_post.call_args
        self.assertEqual(args[0], "anthropic")
        self.assertEqual(args[2]["x-api-key"], "sk-ant")

    @patch("chad.gateway.anthropic.post_json")
    def test_system_message(self, mock_post):
        mock_post.return_value = {"content": [{"type": "text", "text": "ok"}]}
        provider = AnthropicProvider(api_key="sk-ant")
        provider.request(
            "claude-3",
            (_msg("system", "be helpful"), _msg("user", "hi")),
            (),
        )
        body = mock_post.call_args.args[3]
        self.assertEqual(body["system"], "be helpful")
        self.assertEqual(body["messages"][0]["role"], "user")


class GoogleTests(unittest.TestCase):
    @patch("chad.gateway.google.post_json")
    def test_mocked(self, mock_post):
        mock_post.return_value = {
            "candidates": [{"content": {"parts": [{"text": "gemini reply"}]}}]
        }
        provider = GoogleProvider(api_key="sk-google")
        resp = provider.request("gemini-pro", (_msg("user", "hi"),), ())
        self.assertEqual(resp.content, "gemini reply")
        args, _ = mock_post.call_args
        self.assertEqual(args[0], "google")
        self.assertIn("models/gemini-pro:generateContent", args[1])

    @patch("chad.gateway.google.post_json")
    def test_invalid_request_normalized(self, mock_post):
        mock_post.side_effect = InvalidRequestError("google: invalid request")
        provider = GoogleProvider(api_key="sk-google")
        with self.assertRaises(GatewayError):
            provider.request("m", (), ())


if __name__ == "__main__":
    unittest.main()
