import { queryOptions } from "@tanstack/react-query";
import { ApiError, apiRequest, apiUpload } from "@/shared/api";
import {
  importBatchDetailSchema,
  importBatchSchema,
  importSourceTypeSchema,
  type ImportBatch,
  type ImportSourceType,
} from "../model/schema";

const MAX_FILE_SIZE = 25 * 1024 * 1024;

export const importBatchKeys = {
  all: ["import-batch"] as const,
  detail: (batchId: string) => [...importBatchKeys.all, batchId] as const,
};

export interface UploadImportFileInput {
  file: File;
  sourceType: ImportSourceType;
  onProgress?: (loaded: number, total: number) => void;
}

export function importBatchQueryOptions(batchId: string) {
  return queryOptions({
    queryKey: importBatchKeys.detail(batchId),
    queryFn: () => apiRequest(`/api/imports/${encodeURIComponent(batchId)}`, importBatchDetailSchema),
    retry: false,
  });
}

export function uploadImportFile(input: UploadImportFileInput): Promise<ImportBatch> {
  const sourceType = importSourceTypeSchema.parse(input.sourceType);
  if (!input.file.name.toLowerCase().endsWith(".xlsx")) {
    throw new ApiError(0, "Для импорта выберите файл Excel в формате .xlsx.", { code: "invalid_import_file" });
  }
  if (input.file.size === 0 || input.file.size > MAX_FILE_SIZE) {
    throw new ApiError(0, "Размер файла должен быть от 1 байта до 25 МБ.", { code: "invalid_import_file" });
  }
  const body = new FormData();
  body.set("source_type", sourceType);
  body.set("file", input.file, input.file.name);
  return apiUpload("/api/imports", importBatchSchema, body, input.onProgress);
}
