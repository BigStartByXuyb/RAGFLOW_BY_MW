import { Routes } from '@/routes';
import { useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';

export enum QueryStringMap {
  KnowledgeId = 'knowledgeId',
  id = 'id',
}

export const useNavigatePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { id } = useParams();

  const navigateToDatasetList = useCallback(
    ({ isCreate = false }: { isCreate?: boolean }) => {
      if (isCreate) {
        navigate(Routes.Datasets + '?isCreate=true');
      } else {
        navigate(Routes.Datasets);
      }
    },
    [navigate],
  );

  const navigateToMemoryList = useCallback(
    ({ isCreate = false }: { isCreate?: boolean }) => {
      if (isCreate) {
        navigate(Routes.Memories + '?isCreate=true');
      } else {
        navigate(Routes.Memories);
      }
    },
    [navigate],
  );

  const navigateToDataset = useCallback(
    (id: string) => () => {
      // navigate(`${Routes.DatasetBase}${Routes.DataSetOverview}/${id}`);
      navigate(`${Routes.Dataset}/${id}`);
    },
    [navigate],
  );
  const navigateToDatasetOverview = useCallback(
    (id: string) => () => {
      navigate(`${Routes.DatasetBase}${Routes.DataSetOverview}/${id}`);
    },
    [navigate],
  );

  const navigateToDataFile = useCallback(
    (id: string) => () => {
      navigate(`${Routes.DatasetBase}${Routes.Files}/${id}`);
    },
    [navigate],
  );

  const navigateToCompilation = useCallback(
    (id: string) => () => {
      navigate(`${Routes.DatasetBase}${Routes.Compilation}/${id}`);
    },
    [navigate],
  );

  const navigateToHome = useCallback(() => {
    navigate(Routes.Root);
  }, [navigate]);

  const navigateToProfile = useCallback(() => {
    navigate(Routes.ProfileSetting);
  }, [navigate]);

  const navigateToOldProfile = useCallback(() => {
    navigate(Routes.UserSetting);
  }, [navigate]);

  const navigateToChatList = useCallback(() => {
    navigate(Routes.Chats);
  }, [navigate]);

  const navigateToChat = useCallback(
    (id: string) => () => {
      navigate(`${Routes.Chat}/${id}`);
    },
    [navigate],
  );

  const navigateToSearchList = useCallback(() => {
    navigate(Routes.Searches);
  }, [navigate]);

  const navigateToSearch = useCallback(
    (id: string) => () => {
      navigate(`${Routes.Search}/${id}`);
    },
    [navigate],
  );
  const navigateToMemory = useCallback(
    (id: string) => () => {
      navigate(`${Routes.Memory}${Routes.MemoryMessage}/${id}`);
    },
    [navigate],
  );

  const navigateToChunkParsedResult = useCallback(
    (id: string, knowledgeId?: string) => () => {
      navigate(
        `${Routes.ParsedResult}/chunks?id=${knowledgeId}&doc_id=${id}`,
      );
    },
    [navigate],
  );

  const getQueryString = useCallback(
    (queryStringKey?: QueryStringMap) => {
      const allQueryString = {
        [QueryStringMap.KnowledgeId]: searchParams.get(
          QueryStringMap.KnowledgeId,
        ),
        [QueryStringMap.id]: searchParams.get(QueryStringMap.id),
      };
      if (queryStringKey) {
        return allQueryString[queryStringKey];
      }
      return allQueryString;
    },
    [searchParams],
  );

  const navigateToChunk = useCallback(
    (route: Routes) => {
      navigate(
        `${route}/${id}?${QueryStringMap.KnowledgeId}=${getQueryString(QueryStringMap.KnowledgeId)}`,
      );
    },
    [getQueryString, id, navigate],
  );

  const navigateToFiles = useCallback(
    (folderId?: string) => {
      navigate(`${Routes.Files}?folderId=${folderId}`);
    },
    [navigate],
  );

  const navigateToDataSourceDetail = useCallback(
    (id?: string) => {
      navigate(
        `${Routes.UserSetting}${Routes.DataSource}${Routes.DataSourceDetailPage}?id=${id}`,
      );
    },
    [navigate],
  );

  const navigateToModelSetting = useCallback(() => {
    navigate(`${Routes.UserSetting}${Routes.Model}`);
  }, [navigate]);

  const navigateToCompilationTemplates = useCallback(() => {
    navigate(`${Routes.UserSetting}${Routes.CompilationTemplates}`);
  }, [navigate]);

  const navigateToCompilationTemplate = useCallback(
    (id?: string) => () => {
      if (id && id !== 'create') {
        navigate(`${Routes.CompilationTemplatesCreateNext}/${id}`);
      } else {
        navigate(Routes.CompilationTemplatesCreateNext);
      }
    },
    [navigate],
  );

  const navigateToCompilationTemplateEditNext = useCallback(
    (id?: string) => () => {
      if (id && id !== 'create') {
        navigate(`${Routes.CompilationTemplatesEditNext}/${id}`);
      } else {
        navigate(Routes.CompilationTemplatesEditNext);
      }
    },
    [navigate],
  );

  return {
    navigateToDatasetList,
    navigateToDataset,
    navigateToDatasetOverview,
    navigateToHome,
    navigateToProfile,
    navigateToChatList,
    navigateToChat,
    navigateToChunkParsedResult,
    getQueryString,
    navigateToChunk,
    navigateToSearchList,
    navigateToSearch,
    navigateToFiles,
    navigateToOldProfile,
    navigateToDataFile,
    navigateToCompilation,
    navigateToDataSourceDetail,
    navigateToMemory,
    navigateToMemoryList,
    navigateToModelSetting,
    navigateToCompilationTemplates,
    navigateToCompilationTemplate,
    navigateToCompilationTemplateEditNext,
  };
};
