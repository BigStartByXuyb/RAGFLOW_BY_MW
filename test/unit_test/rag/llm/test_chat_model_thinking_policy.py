#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging

import pytest

from rag.llm import SupportedLiteLLMProvider
from rag.llm.chat_model import _apply_claude_sampling_policy, _apply_model_family_policies, _claude_version, _move_litellm_provider_body_fields

pytestmark = pytest.mark.p1


def test_qwen3_uses_system_disabled_default():
    gen_conf, kwargs = _apply_model_family_policies(
        "qwen3-plus",
        backend="base",
        gen_conf={},
        request_kwargs={},
    )

    assert gen_conf == {}
    assert kwargs["extra_body"]["enable_thinking"] is False


def test_qwen3_can_enable_thinking_explicitly():
    gen_conf, kwargs = _apply_model_family_policies(
        "qwen3-plus",
        backend="base",
        gen_conf={"thinking": "enabled", "temperature": 0.2},
        request_kwargs={"extra_body": {"seed": 1}},
    )

    assert gen_conf == {"temperature": 0.2}
    assert kwargs["extra_body"] == {"seed": 1, "enable_thinking": True}


@pytest.mark.parametrize(
    "provider",
    [SupportedLiteLLMProvider.Tongyi_Qianwen, SupportedLiteLLMProvider.Dashscope],
)
def test_qwen3_litellm_provider_uses_provider_field(provider):
    gen_conf, kwargs = _apply_model_family_policies(
        "qwen3-max",
        backend="litellm",
        provider=provider,
        gen_conf={"thinking": "disabled"},
        request_kwargs={},
    )

    assert kwargs == {}
    assert gen_conf["enable_thinking"] is False


def test_kimi_thinking_maps_to_moonshot_payload():
    gen_conf, kwargs = _apply_model_family_policies(
        "kimi-k2.6-preview",
        backend="litellm",
        provider=SupportedLiteLLMProvider.Moonshot,
        gen_conf={"thinking": "disabled", "temperature": 0.6},
        request_kwargs={},
    )

    assert kwargs == {}
    assert gen_conf["thinking"] == {"type": "disabled"}
    assert "temperature" not in gen_conf


def test_moonshot_explicit_thinking_does_not_require_exact_kimi_model_name():
    gen_conf, kwargs = _apply_model_family_policies(
        "kimi-latest",
        backend="litellm",
        provider=SupportedLiteLLMProvider.Moonshot,
        gen_conf={"thinking": "disabled"},
        request_kwargs={},
    )

    assert kwargs == {}
    assert gen_conf["thinking"] == {"type": "disabled"}


def test_kimi_keeps_provider_default_when_unspecified():
    gen_conf, kwargs = _apply_model_family_policies(
        "kimi-k2.5-preview",
        backend="litellm",
        provider=SupportedLiteLLMProvider.Moonshot,
        gen_conf={"temperature": 0.6},
        request_kwargs={},
    )

    assert kwargs == {}
    assert "thinking" not in gen_conf
    assert "temperature" not in gen_conf
    assert gen_conf["top_p"] == 0.95
    assert gen_conf["n"] == 1
    assert gen_conf["presence_penalty"] == 0.0
    assert gen_conf["frequency_penalty"] == 0.0


def test_glm_keeps_provider_default_when_unspecified():
    gen_conf, kwargs = _apply_model_family_policies(
        "glm-4.7",
        backend="litellm",
        provider=SupportedLiteLLMProvider.ZHIPU_AI,
        gen_conf={},
        request_kwargs={},
    )

    assert kwargs == {}
    assert gen_conf == {}


def test_glm_thinking_maps_to_zhipu_payload():
    gen_conf, kwargs = _apply_model_family_policies(
        "glm-4.7",
        backend="litellm",
        provider=SupportedLiteLLMProvider.ZHIPU_AI,
        gen_conf={"thinking": "enabled"},
        request_kwargs={},
    )

    assert kwargs == {}
    assert gen_conf["thinking"] == {"type": "enabled"}


def test_litellm_provider_body_fields_move_to_extra_body_before_drop_params():
    completion_args = {
        "model": "kimi-latest",
        "messages": [],
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
    }

    _move_litellm_provider_body_fields(SupportedLiteLLMProvider.Moonshot, completion_args)

    assert completion_args["extra_body"]["thinking"] == {"type": "disabled"}
    assert "thinking" not in completion_args
    assert completion_args["temperature"] == 0.2


def test_litellm_provider_body_fields_preserve_existing_extra_body():
    completion_args = {
        "model": "qwen3-max",
        "messages": [],
        "enable_thinking": False,
        "extra_body": {"seed": 1},
    }

    _move_litellm_provider_body_fields(SupportedLiteLLMProvider.Tongyi_Qianwen, completion_args)

    assert completion_args["extra_body"] == {"seed": 1, "enable_thinking": False}
    assert "enable_thinking" not in completion_args


CLAUDE_GEN_CONF = {"temperature": 0.8, "top_p": 0.9, "presence_penalty": 0.1, "frequency_penalty": 0.1}


def _litellm_policies(model_name, provider, gen_conf):
    sanitized, _ = _apply_model_family_policies(model_name, backend="litellm", provider=provider, gen_conf=gen_conf)
    return sanitized


def test_bedrock_claude_keeps_temperature_and_drops_top_p():
    gen_conf = _litellm_policies("eu.anthropic.claude-sonnet-4-6", SupportedLiteLLMProvider.Bedrock, CLAUDE_GEN_CONF)

    assert gen_conf["temperature"] == 0.8
    assert "top_p" not in gen_conf
    assert gen_conf["presence_penalty"] == 0.1


def test_bedrock_claude_top_p_alone_is_preserved():
    gen_conf = _litellm_policies("eu.anthropic.claude-sonnet-4-6", SupportedLiteLLMProvider.Bedrock, {"top_p": 0.9})

    assert gen_conf == {"top_p": 0.9}


@pytest.mark.parametrize(
    "model_name",
    [
        "eu.anthropic.claude-opus-4-7-v1",
        "eu.anthropic.claude-opus-4-8-v1:0",
        "eu.anthropic.claude-opus-5",
        "eu.anthropic.claude-sonnet-5",
        "anthropic.claude-fable-5-1",
    ],
)
def test_bedrock_claude_without_sampling_support_drops_all_sampling_params(model_name):
    gen_conf = _litellm_policies(model_name, SupportedLiteLLMProvider.Bedrock, {**CLAUDE_GEN_CONF, "top_k": 40})

    assert not {"temperature", "top_p", "top_k"} & set(gen_conf)
    assert gen_conf["presence_penalty"] == 0.1


def test_claude_sonnet_4_5_is_not_matched_as_sonnet_5():
    gen_conf = _litellm_policies("eu.anthropic.claude-sonnet-4-5", SupportedLiteLLMProvider.Bedrock, CLAUDE_GEN_CONF)

    assert gen_conf["temperature"] == 0.8
    assert "top_p" not in gen_conf


def test_anthropic_opus_4_8_still_drops_all_sampling_params():
    gen_conf = _litellm_policies("claude-opus-4-8", SupportedLiteLLMProvider.Anthropic, CLAUDE_GEN_CONF)

    assert not {"temperature", "top_p", "top_k"} & set(gen_conf)


def test_bedrock_non_claude_model_is_untouched():
    gen_conf = _litellm_policies("mistral.mistral-large-2402-v1:0", SupportedLiteLLMProvider.Bedrock, CLAUDE_GEN_CONF)

    assert gen_conf == CLAUDE_GEN_CONF


def test_claude_sampling_policy_drops_top_p_across_targets_when_temperature_is_anywhere():
    gen_conf, kwargs = {"top_p": 0.9}, {"temperature": 0.2}

    _apply_claude_sampling_policy("eu.anthropic.claude-sonnet-4-6", gen_conf, kwargs)

    assert gen_conf == {}
    assert kwargs == {"temperature": 0.2}


def test_claude_sampling_policy_logs_applied_policy(caplog):
    with caplog.at_level(logging.DEBUG):
        _apply_claude_sampling_policy("eu.anthropic.claude-sonnet-4-6", {"temperature": 0.8, "top_p": 0.9})
        _apply_claude_sampling_policy("eu.anthropic.claude-opus-4-8-v1:0", {"temperature": 0.8})
        _apply_claude_sampling_policy("eu.anthropic.claude-sonnet-4-6", {"top_p": 0.9})

    records = [record for record in caplog.records if "Claude sampling policy" in record.getMessage()]
    assert [record.levelno for record in records] == [logging.WARNING, logging.WARNING]
    messages = [record.getMessage() for record in records]
    assert "dropped top_p for model eu.anthropic.claude-sonnet-4-6" in messages[0]
    assert "dropped temperature for model eu.anthropic.claude-opus-4-8-v1:0" in messages[1]


def test_claude_sampling_policy_no_sampling_model_without_params_does_not_log(caplog):
    gen_conf = {"presence_penalty": 0.1}

    with caplog.at_level(logging.DEBUG):
        _apply_claude_sampling_policy("eu.anthropic.claude-opus-4-8-v1:0", gen_conf, {})

    assert gen_conf == {"presence_penalty": 0.1}
    assert not [record for record in caplog.records if "Claude sampling policy" in record.getMessage()]


@pytest.mark.parametrize(
    ("model_name", "expected"),
    [
        ("claude-sonnet-4-5", (4, 5)),
        ("claude-sonnet-4-5-20250929", (4, 5)),
        ("claude-opus-4-1-20250805", (4, 1)),
        ("claude-sonnet-4-20250514", (4, 0)),
        ("us.anthropic.claude-sonnet-4-20250514-v1:0", (4, 0)),
        ("eu.anthropic.claude-sonnet-4-6", (4, 6)),
        ("claude-haiku-4-5-20251001", (4, 5)),
        ("claude-fable-5-1", (5, 1)),
        ("claude-3-5-sonnet-20241022", (3, 5)),
        ("anthropic.claude-3-7-sonnet-20250219-v1:0", (3, 7)),
        ("claude-3-haiku-20240307", (3, 0)),
        ("claude-instant-1.2", None),
    ],
)
def test_claude_version_parsing(model_name, expected):
    assert _claude_version(model_name) == expected


@pytest.mark.parametrize("provider", [SupportedLiteLLMProvider.Anthropic, SupportedLiteLLMProvider.Bedrock])
@pytest.mark.parametrize(
    "model_name",
    ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-sonnet-4-20250514", "anthropic.claude-opus-4-20250514-v1:0"],
)
def test_claude_before_4_1_keeps_temperature_and_top_p(model_name, provider):
    gen_conf = _litellm_policies(model_name, provider, CLAUDE_GEN_CONF)

    assert gen_conf == CLAUDE_GEN_CONF


@pytest.mark.parametrize("provider", [SupportedLiteLLMProvider.Anthropic, SupportedLiteLLMProvider.Bedrock])
@pytest.mark.parametrize("model_name", ["claude-opus-4-1-20250805", "claude-sonnet-4-5", "claude-haiku-4-5-20251001", "claude-opus-4-6"])
def test_claude_4_1_and_later_drop_top_p_on_both_providers(model_name, provider):
    gen_conf = _litellm_policies(model_name, provider, CLAUDE_GEN_CONF)

    assert gen_conf["temperature"] == 0.8
    assert "top_p" not in gen_conf


def test_claude_with_unparsable_version_is_treated_as_recent():
    gen_conf = _litellm_policies("claude-latest", SupportedLiteLLMProvider.Anthropic, CLAUDE_GEN_CONF)

    assert "top_p" not in gen_conf
