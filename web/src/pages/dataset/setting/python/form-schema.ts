import { DESCRIPTION_MAX_LENGTH } from '@/constants/common';
import { t } from 'i18next';
import { z } from 'zod';

export const formSchema = z.object({
    name: z.string().min(1, {
      message: 'Username must be at least 2 characters.',
    }),
    description: z
      .string()
      .max(DESCRIPTION_MAX_LENGTH, {
        message: t('common.descriptionMaxLength', {
          max: DESCRIPTION_MAX_LENGTH,
        }),
      })
      .optional(),
    // avatar: z.instanceof(File),
    avatar: z.any().nullish(),
    permission: z.string().optional(),
    language: z.string().optional(),
    chunk_method: z.string(),
    embedding_model: z.string(),
    parser_config: z
      .object({
        layout_recognize: z.string(),
        chunk_token_num: z.number(),
        delimiter: z.string(),
        enable_children: z.boolean(),
        children_delimiter: z.string(),
        auto_keywords: z.number().optional(),
        auto_questions: z.number().optional(),
        html4excel: z.boolean(),
        tag_kb_ids: z.array(z.string()).nullish(),
        topn_tags: z.number().optional(),
        image_table_context_window: z.number().optional(),
        overlapped_percent: z.number().optional(),
        // MinerU-specific options
        mineru_parse_method: z.enum(['auto', 'txt', 'ocr']).optional(),
        mineru_formula_enable: z.boolean().optional(),
        mineru_table_enable: z.boolean().optional(),
        mineru_lang: z.string().optional(),
        metadata: z.any().optional(),
        built_in_metadata: z
          .array(
            z.object({
              key: z.string().optional(),
              type: z.string().optional(),
            }),
          )
          .optional(),
        enable_metadata: z.boolean().optional(),
        llm_id: z.string().optional(),
        // Table parser: "auto" = all columns both, "manual" = use column role selector
        table_column_mode: z.enum(['auto', 'manual']).optional(),
        // Table parser: column name -> role (indexing | metadata | both); legacy "vectorize" -> indexing
        table_column_roles: z
          .record(
            z
              .enum(['indexing', 'metadata', 'both', 'vectorize'])
              .transform((role) => (role === 'vectorize' ? 'indexing' : role)),
          )
          .optional(),
        // Table parser: column names list (set by backend after first parse)
        table_column_names: z.array(z.string()).optional(),
      })
      .optional(),
    pagerank: z.number(),
    connectors: z
      .array(
        z.object({
          id: z.string().optional(),
          name: z.string().optional(),
          source: z.string().optional(),
          ststus: z.string().optional(),
          auto_parse: z.string().optional(),
        }),
      )
      .optional(),
    // icon: z.array(z.instanceof(File)),
  });
