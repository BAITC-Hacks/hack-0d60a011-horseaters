import { z } from "zod";

const PRECISION = 10_000;

function scaledQuantity(value: number): number | null {
  const scaled = value * PRECISION;
  const rounded = Math.round(scaled);
  return Number.isSafeInteger(rounded) && Math.abs(scaled - rounded) < 0.000001 ? rounded : null;
}

export function adjustmentFormSchema(moq: number, packageSize: number) {
  return z.strictObject({
    new_quantity: z.number({ error: "Укажите количество." }).finite("Количество должно быть числом.").nonnegative("Количество не может быть отрицательным."),
    reason: z.string().trim().min(1, "Укажите причину изменения.").max(2000, "Не более 2000 символов."),
  }).superRefine(({ new_quantity }, context) => {
    const quantityUnits = scaledQuantity(new_quantity);
    if (quantityUnits === null) {
      context.addIssue({ code: "custom", path: ["new_quantity"], message: "Допускается не более четырёх знаков после запятой." });
      return;
    }
    if (quantityUnits === 0) return;

    const moqUnits = scaledQuantity(moq);
    const packageUnits = scaledQuantity(packageSize);
    if (moqUnits === null || packageUnits === null || moqUnits <= 0 || packageUnits <= 0) {
      context.addIssue({ code: "custom", path: ["new_quantity"], message: "Сервер не предоставил корректные условия поставки." });
      return;
    }
    if (quantityUnits < moqUnits) {
      context.addIssue({ code: "custom", path: ["new_quantity"], message: `Минимальная партия — ${moq}.` });
    }
    if (quantityUnits % packageUnits !== 0) {
      context.addIssue({ code: "custom", path: ["new_quantity"], message: `Количество должно быть кратно ${packageSize}.` });
    }
  });
}

export type AdjustmentFormValues = z.infer<ReturnType<typeof adjustmentFormSchema>>;
