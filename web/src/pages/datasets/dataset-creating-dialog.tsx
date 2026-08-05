import { BuiltinPipelineItem } from '@/components/builtin-pipeline-form-field';
import { ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { useFetchDefaultModelDictionary } from '@/hooks/use-llm-request';
import { IModalProps } from '@/interfaces/common';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import {
  ChunkMethodItem,
  EmbeddingModelItem,
} from '../dataset/dataset-setting/configuration/common-item';
import { isGoBackend } from '@/utils/backend-runtime';

const FormId = 'dataset-creating-form';

export function InputForm({ onOk }: IModalProps<any>) {
  const { t } = useTranslation();
  const defaultModelDictionary = useFetchDefaultModelDictionary(true);
  const ChunkMethodName = isGoBackend() ? 'parser_id' : 'chunk_method';

  const FormSchema = z
    .object({
      name: z
        .string()
        .min(1, {
          message: t('knowledgeList.namePlaceholder'),
        })
        .trim(),
      embedding_model: z
        .string()
        .min(1, {
          message: t('knowledgeConfiguration.embeddingModelPlaceholder'),
        })
        .trim(),
      [ChunkMethodName]: z.string().optional(),
    })
    .superRefine((data, ctx) => {
      if (!data[ChunkMethodName] || data[ChunkMethodName].trim() === '') {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('knowledgeList.parserRequired'),
          path: [ChunkMethodName],
        });
      }
    });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      name: '',
      [ChunkMethodName]: '',
      embedding_model: defaultModelDictionary?.embd_id,
    },
  });

  function onSubmit(data: z.infer<typeof FormSchema>) {
    onOk?.(data);
  }

  useEffect(() => {
    if (defaultModelDictionary?.embd_id) {
      form.setValue('embedding_model', defaultModelDictionary?.embd_id);
    }
  }, [form, defaultModelDictionary]);

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit, (errors) => {
          console.warn(errors);
        })}
        className="space-y-6"
        id={FormId}
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem className="space-y-1">
              <FormLabel required>{t('knowledgeList.name')}</FormLabel>
              <FormControl>
                <Input
                  placeholder={t('knowledgeList.namePlaceholder')}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <EmbeddingModelItem line={2} isEdit={false} />
        {isGoBackend() ? (
          <BuiltinPipelineItem name={ChunkMethodName} />
        ) : (
          <ChunkMethodItem name={ChunkMethodName} />
        )}
      </form>
    </Form>
  );
}

export function DatasetCreatingDialog({
  hideModal,
  onOk,
  loading,
}: IModalProps<any>) {
  const { t } = useTranslation();

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent
        className="sm:max-w-[425px] focus-visible:!outline-none flex flex-col"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const form = document.getElementById(FormId) as HTMLFormElement;
            form?.requestSubmit();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{t('knowledgeList.createKnowledgeBase')}</DialogTitle>
        </DialogHeader>
        <DialogDescription></DialogDescription>
        <InputForm onOk={onOk}></InputForm>
        <DialogFooter>
          <ButtonLoading type="submit" form={FormId} loading={loading}>
            {t('common.save')}
          </ButtonLoading>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
