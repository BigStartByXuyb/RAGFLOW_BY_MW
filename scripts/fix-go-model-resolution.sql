-- Make an existing (Python-era) tenant resolvable by the Go ingestion path.
--
-- Background: Go resolves a knowledge base's `embd_id` such as
-- "qwen3.7-text-embedding@Tongyi-Qianwen" through parseModelName
-- (go/service/model_service.go), which maps the 2-segment form to a model
-- instance literally named "default". Python-era rows never created such an
-- instance and store the full compatible-mode path in the instance base_url,
-- so Go ingestion fails with:
--
--   resolve embedder: instance "default" lookup failed: record not found
--   Aliyun embeddings API error: 404 Not Found
--
-- Fix 1: the provider's model instance must be named "default". The Python side
-- only reads tenant_llm, so renaming the instance is safe for both backends.
-- (Renaming to "default" is preferred over rewriting embd_id to the 3-segment
-- "model@instance@provider" form: Python's split_model_name_and_factory would
-- then treat "model@instance" as the llm_name and fail its tenant_llm lookup.)
--
-- Fix 2: conf/models/aliyun.json already contributes
-- "compatible-mode/v1/embeddings" via url_suffix.embedding, so the instance
-- base_url override must be the host root only; otherwise the path is
-- duplicated into ".../compatible-mode/v1/compatible-mode/v1/embeddings".
--
-- Replace the ids with the ones from your own tenant_model_instance rows.

use rag_flow;

UPDATE tenant_model_instance
SET instance_name = 'default'
WHERE id = 'ff572d9cb33811f18fb61f4fc60efec8';

UPDATE tenant_model_instance
SET extra = '{"base_url": "https://dashscope.aliyuncs.com"}'
WHERE id = 'ff572d9cb33811f18fb61f4fc60efec8';

SELECT id, instance_name, extra FROM tenant_model_instance;
