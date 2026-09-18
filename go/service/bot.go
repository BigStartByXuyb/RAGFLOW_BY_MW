//
//  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

// BotService is the shared service layer for the public chatbot
// endpoints (api/v1/chatbots/...) plus the agent attachment
// download. It is intentionally a thin aggregator — it sequences
// DAO lookups, the tenant/status authorisation guard, and delegates
// the heavy work (LLM call) to the existing services.
package service

import (
	"context"
	"errors"
	"hash/fnv"
	"strings"
	"sync"

	"ragflow/go/common"
	"ragflow/go/dao"
	"ragflow/go/entity"
)

// BotService coordinates chatbot reads and the matching completion
// paths. Mirrors the Python
// `api/db/services/conversation_service.py::async_iframe_completion`
// + `api/db/services/canvas_service.py::completion` flow but stays
// stateless — it does not own the LLM or canvas runner; it just
// sequences them.
type BotService struct {
	chatDAO             *dao.ChatSessionDAO
	canvasDAO           *dao.UserCanvasDAO
	api4ConversationDAO *dao.API4ConversationDAO
	agentService        *AgentService
	llmService          *LLMService
	pipeline            *ChatPipelineService
	// persistLocks serialises persistChatbotTurn's read-modify-write
	// on a single api_4_conversation row. ChatbotCompletion fetches
	// the session before streaming starts, so without this lock two
	// concurrent requests on the same session_id would each append
	// their turn to the same stale base and the last Update would
	// silently drop the other exchange. Striped to a fixed size so
	// the lock set does not grow with the number of sessions.
	persistLocks [64]sync.Mutex
}

// NewBotService wires a fresh BotService. llmSvc is required for
// ChatbotCompletion (in
// step 6). Both are nullable in unit tests.
func NewBotService(agentSvc *AgentService, llmSvc *LLMService) *BotService {
	return &BotService{
		chatDAO:             dao.NewChatSessionDAO(),
		canvasDAO:           dao.NewUserCanvasDAO(),
		api4ConversationDAO: dao.NewAPI4ConversationDAO(),
		agentService:        agentSvc,
		llmService:          llmSvc,
		pipeline:            NewChatPipelineService(),
	}
}

// ChatbotInfo returns the public metadata of a chatbot dialog.
//
// Mirrors the python `bot_api.py::chatbot_info` handler. The
// authorisation check is: dialog must exist, the requester must own
// it (TenantID match), and Status must equal common.StatusDialogValid
// (the python StatusEnum.VALID.value).
func (s *BotService) ChatbotInfo(ctx context.Context, tenantID, dialogID string) (
	title, avatar, prologue, llmID string, hasTavilyKey bool, ec common.ErrorCode, err error,
) {
	dialog, err := s.chatDAO.GetDialogByID(ctx, dao.DB, dialogID)
	if err != nil {
		return "", "", "", "", false, common.CodeDataError, err
	}
	if dialog == nil || dialog.TenantID != tenantID ||
		dialog.Status == nil || *dialog.Status != common.StatusDialogValid {
		return "", "", "", "", false, common.CodeDataError,
			errors.New("Authentication error: no access to this chatbot!")
	}
	pc := dialog.PromptConfig
	// Defensive lookups mirroring python's
	// dialog.prompt_config.get("prologue", "") and
	// dialog.prompt_config.get("tavily_api_key", "").strip()
	// semantics. A hard type assertion here would panic on a missing
	// or non-string prologue field — this endpoint is public over
	// persisted JSON config and the schema is not guaranteed.
	prologue = stringFromMap(pc, "prologue")
	tk := stringFromMap(pc, "tavily_api_key")
	return botDerefStr(dialog.Name), botDerefStr(dialog.Icon), prologue,
		dialog.LLMID, strings.TrimSpace(tk) != "", common.CodeSuccess, nil
}

// ChatbotCompletionRequest is the request body for
// /api/v1/chatbots/<dialog_id>/completions. Mirrors the python
// `async_iframe_completion` body shape (session_id, question,
// tts (unused) and a freeform dict).
type ChatbotCompletionRequest struct {
	SessionID string         `json:"session_id"`
	Question  string         `json:"question"`
	Stream    bool           `json:"stream"`
	Inputs    map[string]any `json:"inputs"`
	// Quote controls citation generation. Nil means "absent" —
	// python bot_api.py defaults it to False for chatbot
	// completions, so the service layer mirrors that.
	Quote *bool `json:"quote"`
	// Reasoning / Internet arrive as bool OR 0/1 number depending
	// on the widget; the service layer normalises them before
	// handing them to the chat pipeline.
	Reasoning any `json:"reasoning"`
	Internet  any `json:"internet"`
	// DocIDs is an optional comma-separated document filter,
	// same shape as the regular chat completion kwargs.
	DocIDs string `json:"doc_ids"`
}

// persistLock returns the striped mutex guarding one session row's
// read-modify-write in persistChatbotTurn. The modulo runs on the
// unsigned hash — converting to int first would go negative on
// 32-bit architectures and panic with an out-of-bounds index.
func (s *BotService) persistLock(sessionID string) *sync.Mutex {
	h := fnv.New32a()
	_, _ = h.Write([]byte(sessionID))
	return &s.persistLocks[h.Sum32()%uint32(len(s.persistLocks))]
}

// botDerefStr returns *s or "" if nil. Used to read pointer-string
// fields on entities (Name, Icon, Title, Avatar). Prefixed with bot
// to avoid colliding with the test-only botDerefStr in
// openai_chat_test.go.
func botDerefStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// stringFromMap returns m[key] as a string. Returns "" if the key is
// absent or the value is not a string. Used for defensive reads
// over JSONMap-shaped fields (dialog.prompt_config) where a hard
// type assertion would panic.
func stringFromMap(m entity.JSONMap, key string) string {
	if m == nil {
		return ""
	}
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}
