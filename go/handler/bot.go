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

package handler

import (
	"context"

	"github.com/gin-gonic/gin"

	"ragflow/go/common"
	"ragflow/go/service"
)

// BotHandler is the handler for the public chatbot endpoints
// mounted on /api/v1/chatbots/*. They are authenticated with
// BetaAuthMiddleware (set up at registration time via g.Use(mw)).
type BotHandler struct {
	botService botService
}

// botService is the subset of BotService used by these handlers. It
// is interface-typed so the test suite can inject a stub.
type botService interface {
	ChatbotInfo(ctx context.Context, tenantID, dialogID string) (
		title, avatar, prologue, llmID string, hasTavilyKey bool, ec common.ErrorCode, err error)
	ChatbotCompletion(ctx context.Context, tenantID, dialogID string, req service.ChatbotCompletionRequest) (
		<-chan service.ChatbotSSEFrame, common.ErrorCode, error)
}

// NewBotHandler wires a BotHandler with the production BotService.
func NewBotHandler(svc *service.BotService) *BotHandler {
	return &BotHandler{botService: svc}
}

// ChatbotInfo GET /api/v1/chatbots/<dialog_id>/info
//
// Mirrors python bot_api.py:126-154. Returns the public metadata of
// a chatbot dialog (title, avatar, prologue, tavily key flag, llm_id).
func (h *BotHandler) ChatbotInfo(c *gin.Context) {
	user, code, msg := GetUser(c)
	if code != common.CodeSuccess {
		common.ResponseWithCodeData(c, code, nil, msg)
		return
	}
	dialogID := c.Param("dialog_id")
	if dialogID == "" {
		common.ResponseWithCodeData(c, common.CodeArgumentError, nil, "`dialog_id` is required.")
		return
	}
	title, avatar, prologue, llmID, hasTavily, ec, err := h.botService.ChatbotInfo(
		c.Request.Context(), user.ID, dialogID)
	if err != nil {
		common.ResponseWithCodeData(c, ec, nil, err.Error())
		return
	}
	common.SuccessWithData(c, gin.H{
		"title":          title,
		"avatar":         avatar,
		"prologue":       prologue,
		"has_tavily_key": hasTavily,
		"llm_id":         llmID,
	}, "success")
}

// ChatbotCompletion POST /api/v1/chatbots/<dialog_id>/completions
//
// Mirrors python bot_api.py:55 (async_iframe_completion). Streams
// SSE frames in the Python envelope shape. The streaming helper
// lives in service/bot_completion.go.
func (h *BotHandler) ChatbotCompletion(c *gin.Context) {
	user, code, msg := GetUser(c)
	if code != common.CodeSuccess {
		common.ResponseWithCodeData(c, code, nil, msg)
		return
	}
	dialogID := c.Param("dialog_id")
	if dialogID == "" {
		common.ResponseWithCodeData(c, common.CodeArgumentError, nil, "`dialog_id` is required.")
		return
	}
	var body service.ChatbotCompletionRequest
	// ContentLength != 0 (not > 0) so chunked requests carrying a
	// valid JSON body with ContentLength == -1 still bind. The old
	// `> 0` guard silently dropped those payloads and the chatbot
	// then ran with empty session_id/question.
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&body); err != nil {
			common.ResponseWithCodeData(c, common.CodeArgumentError, nil,
				"Invalid request: "+err.Error())
			return
		}
	}
	frames, ec, err := h.botService.ChatbotCompletion(
		c.Request.Context(), user.ID, dialogID, body)
	if err != nil {
		common.ResponseWithCodeData(c, ec, nil, err.Error())
		return
	}
	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	for f := range frames {
		if f.Done {
			if err := service.WriteDoneFrame(c.Writer); err != nil {
				return
			}
			continue
		}
		if err := service.WriteChatbotFrame(c.Writer, f); err != nil {
			return
		}
	}
}

