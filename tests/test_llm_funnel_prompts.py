"""Tests for funnel-aware prompt builders."""

from unittest.mock import MagicMock

import pytest

from app.llm.prompts import (
    build_initial_user_prompt,
    build_reply_user_prompt,
    build_system_prompt,
)


class TestBuildSystemPrompt:
    def test_hook_stage_has_no_cta(self):
        script = MagicMock(
            role_prompt="Sales",
            target_audience="Startups",
            goal="Book",
            success_criteria="Meeting",
            tone="friendly",
            language="ru",
            emoji_policy="forbidden",
            call_to_action="15-минутный созвон",
            sales_funnel=None,
        )
        prompt = build_system_prompt(script, conversation_stage="hook")
        assert "ТЕКУЩИЙ ЭТАП ВОРОНКИ: hook" in prompt
        assert "Запрещено предлагать созвон" in prompt

    def test_cta_stage_allows_cta(self):
        script = MagicMock(
            role_prompt="Sales",
            target_audience=None,
            goal="Book",
            success_criteria=None,
            tone="professional",
            language="ru",
            emoji_policy="forbidden",
            call_to_action="демо",
            sales_funnel=None,
        )
        prompt = build_system_prompt(script, conversation_stage="cta")
        assert "можешь предложить демо" in prompt


class TestBuildInitialUserPrompt:
    def test_first_message_is_hook(self):
        script = MagicMock(
            sales_funnel=None,
            max_first_message_length=150,
            call_to_action="созвон",
        )
        contact = MagicMock(
            first_name="Alice",
            company_name="Acme",
            position="CEO",
            city=None,
            industry=None,
        )
        prompt = build_initial_user_prompt(script, contact, "hook")
        assert "ПЕРВОЕ сообщение" in prompt
        assert "Alice" in prompt
        assert "Acme" in prompt
        assert "CEO" in prompt
        assert "Не предлагай созвон" in prompt


class TestBuildReplyUserPrompt:
    def test_reply_prompt_includes_stage(self):
        script = MagicMock(
            sales_funnel=None,
            call_to_action="созвон",
        )
        prompt = build_reply_user_prompt(
            script,
            conversation_history=[],
            lead_facts={},
            last_agent_message="Привет",
            lead_message="Расскажите",
            conversation_stage="qualification",
        )
        assert "Текущий этап воронки: qualification" in prompt
        assert "НЕЛЬЗЯ предлагать созвон" in prompt
