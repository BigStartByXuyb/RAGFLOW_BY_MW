import { DocumentParserType } from '@/constants/knowledge';
import { useFetchKnowledgeList } from '@/hooks/use-knowledge-request';
import { IDataset } from '@/interfaces/database/dataset';
import { useDebounce } from 'ahooks';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { RAGFlowAvatar } from './ragflow-avatar';
import { RAGFlowFormItem } from './ragflow-form';
import { MultiSelect } from './ui/multi-select';


function DatasetLabel({ text }: { text: string }) {
  return (
    <div className="text-xs px-3 p-1 bg-bg-card text-text-secondary rounded-lg border border-bg-card">
      {text}
    </div>
  );
}

export function useDisableDifferenceEmbeddingDataset(name: string) {
  const form = useFormContext();
  const datasetId = useWatch({ name, control: form.control });
  const [searchString, setSearchString] = useState('');
  const debouncedSearchString = useDebounce(searchString, { wait: 500 });
  const {
    list: datasetListOrigin,
    loading,
    handleScroll,
    hasNextPage,
  } = useFetchKnowledgeList(false, debouncedSearchString);
  const datasetCacheRef = useRef(new Map<string, IDataset>());

  const datasetList = useMemo(() => {
    datasetListOrigin.forEach((dataset) => {
      datasetCacheRef.current.set(dataset.id, dataset);
    });

    const selectedDatasetIds = Array.isArray(datasetId) ? datasetId : [];
    const selectedDatasets = selectedDatasetIds
      .map((id) => datasetCacheRef.current.get(id))
      .filter(Boolean) as IDataset[];

    return Array.from(
      new Map(
        [...datasetListOrigin, ...selectedDatasets].map((dataset) => [
          dataset.id,
          dataset,
        ]),
      ).values(),
    );
  }, [datasetId, datasetListOrigin]);

  const selectedEmbedId = useMemo(() => {
    const data = datasetList?.find((item) => item.id === datasetId?.[0]);
    return data?.embedding_model ?? '';
  }, [datasetId, datasetList]);

  const nextOptions = useMemo(() => {
    const datasetListMap = datasetList.map((item: IDataset) => {
      return {
        label: item.name,
        icon: () => (
          <RAGFlowAvatar
            className="size-4"
            avatar={item.avatar}
            name={item.name}
          />
        ),
        suffix: (
          <section className="flex gap-2">
            <DatasetLabel text={item.nickname} />
            <DatasetLabel text={item.embedding_model} />
          </section>
        ),
        value: item.id,
        disabled:
          item.chunk_count <= 0 ||
          item.chunk_method === DocumentParserType.Tag ||
          (item.embedding_model !== selectedEmbedId && selectedEmbedId !== ''),
      };
    });

    return datasetListMap;
  }, [datasetList, selectedEmbedId]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchString(value);
  }, []);

  return {
    datasetOptions: nextOptions,
    handleSearchChange,
    loading,
    searchString,
    handleScroll,
    hasNextPage,
  };
}

export function KnowledgeBaseFormField({
  showVariable = false,
  name = 'dataset_ids',
  required = false,
}: {
  showVariable?: boolean;
  name?: string;
  required?: boolean;
}) {
  const { t } = useTranslation();

  const {
    datasetOptions,
    handleSearchChange,
    loading,
    searchString,
    handleScroll,
    hasNextPage,
  } = useDisableDifferenceEmbeddingDataset(name);

  const knowledgeOptions = datasetOptions;
  const options = useMemo(() => {
    return knowledgeOptions;
  }, [knowledgeOptions]);

  return (
    <RAGFlowFormItem
      name={name}
      tooltip={t('chat.knowledgeBasesTip')}
      required={required}
      label={t('chat.knowledgeBases')}
    >
      {(field) => (
        <MultiSelect
          data-testid="chat-datasets-combobox"
          options={options}
          onValueChange={field.onChange}
          placeholder={t('chat.knowledgeBasesPlaceholder')}
          variant="inverted"
          maxCount={100}
          defaultValue={field.value}
          showSelectAll={false}
          popoverTestId="datasets-options"
          optionTestIdPrefix="datasets"
          searchValue={searchString}
          onSearchChange={handleSearchChange}
          isSearching={loading}
          shouldFilter={false}
          onListScroll={hasNextPage ? handleScroll : undefined}
          {...field}
        />
      )}
    </RAGFlowFormItem>
  );
}
