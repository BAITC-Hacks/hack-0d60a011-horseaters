import { z } from "zod";

export const importSourceSchema = z.enum([
  "sales",
  "monthly_sales",
  "inventory",
  "stockout",
  "in_transit",
  "seasonality",
  "supplier_terms",
  "growth",
  "material_requirements",
]);

const MAX_FILE_SIZE = 25 * 1024 * 1024;

export const importFormSchema = z.strictObject({
  sourceType: importSourceSchema,
  file: z.custom<File>(
    (value) => typeof File !== "undefined" && value instanceof File,
    { message: "Выберите Excel-файл." },
  ).refine((file) => file.name.toLowerCase().endsWith(".xlsx"), {
    message: "Допустим только файл .xlsx.",
  }).refine((file) => file.size > 0, {
    message: "Файл пустой.",
  }).refine((file) => file.size <= MAX_FILE_SIZE, {
    message: "Размер файла не должен превышать 25 МБ.",
  }),
});

export type ImportFormInput = z.infer<typeof importFormSchema>;
