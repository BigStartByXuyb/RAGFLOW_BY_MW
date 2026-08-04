#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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

"""
Unit tests for EmbeddingUtils module.
"""

from rag.svr.task_executor_refactor.embedding_utils import EmbeddingUtils


class TestEmbeddingUtilsPrepareTexts:
    """Tests for prepare_texts_for_embedding class method."""

    def test_prepare_texts_basic(self):
        """Test basic text preparation."""
        docs = [
            {"docnm_kwd": "Title1", "content_with_weight": "Content1"},
            {"docnm_kwd": "Title2", "content_with_weight": "Content2"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert titles == ["Title1", "Title2"]
        assert contents == ["Content1", "Content2"]

    def test_prepare_texts_with_question_kwd(self):
        """Test text preparation with question_kwd."""
        docs = [
            {"docnm_kwd": "Title1", "question_kwd": ["Q1", "Q2"], "content_with_weight": "Content1"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert titles == ["Title1"]
        assert contents == ["Q1\nQ2"]

    def test_prepare_texts_with_empty_question_kwd(self):
        """Test text preparation with empty question_kwd falls back to content."""
        docs = [
            {"docnm_kwd": "Title1", "question_kwd": [], "content_with_weight": "Content1"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert contents == ["Content1"]

    def test_prepare_texts_with_missing_question_kwd(self):
        """Test text preparation without question_kwd uses content."""
        docs = [
            {"docnm_kwd": "Title1", "content_with_weight": "Content1"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert contents == ["Content1"]

    def test_prepare_texts_normalizes_table_html(self):
        """Test that table HTML tags are normalized."""
        docs = [
            {"docnm_kwd": "Title1", "content_with_weight": "<table><tr><td>Cell</td></tr></table>"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        # Table tags should be replaced with spaces
        assert "<table>" not in contents[0]

    def test_prepare_texts_whitespace_only_becomes_none(self):
        """Test that whitespace-only content becomes 'None'."""
        docs = [
            {"docnm_kwd": "Title1", "content_with_weight": "   \n\n  "},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert contents == ["None"]

    def test_prepare_texts_default_title(self):
        """Test that missing docnm_kwd uses 'Title' as default."""
        docs = [
            {"content_with_weight": "Content1"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs)
        assert titles == ["Title"]

    def test_prepare_texts_without_question_kwd(self):
        """Test text preparation with use_question_kwd=False."""
        docs = [
            {"docnm_kwd": "Title1", "question_kwd": ["Q1"], "content_with_weight": "Content1"},
        ]
        titles, contents = EmbeddingUtils.prepare_texts_for_embedding(docs, use_question_kwd=False)
        assert contents == ["Content1"]


class TestEmbeddingUtilsConstants:
    """Tests for class constants."""

    def test_default_title_weight(self):
        """Test DEFAULT_TITLE_WEIGHT value."""
        assert EmbeddingUtils.DEFAULT_TITLE_WEIGHT == 0.1

    def test_default_title_placeholder(self):
        """Test DEFAULT_TITLE_PLACEHOLDER value."""
        assert EmbeddingUtils.DEFAULT_TITLE_PLACEHOLDER == "Title"

    def test_content_placeholder_for_whitespace(self):
        """Test CONTENT_PLACEHOLDER_FOR_WHITESPACE value."""
        assert EmbeddingUtils.CONTENT_PLACEHOLDER_FOR_WHITESPACE == "None"
