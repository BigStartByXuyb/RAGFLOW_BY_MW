import { ChunkMethodDialog } from '@/components/chunk-method-dialog';
import { IDocumentInfo } from '@/interfaces/database/document';
import { IChangeParserRequestBody } from '@/interfaces/request/document';
import { getExtension } from '@/utils/document-util';

type ChangeParserDialogProps = {
  record: IDocumentInfo;
  visible: boolean;
  onOk: (values: IChangeParserRequestBody) => Promise<void>;
  hideModal: () => void;
  loading: boolean;
};

export function ChangeParserDialog({
  record,
  visible,
  onOk,
  hideModal,
  loading,
}: ChangeParserDialogProps) {
  return (
    <ChunkMethodDialog
      documentId={record.id}
      parserId={record.chunk_method}
      parserConfig={record.parser_config}
      documentExtension={getExtension(record.name)}
      onOk={onOk}
      visible={visible}
      hideModal={hideModal}
      loading={loading}
    ></ChunkMethodDialog>
  );
}
