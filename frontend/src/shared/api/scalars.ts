import { z } from "zod";

const decimalTextSchema = z.string()
  .regex(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/)
  .transform(Number);

// Pydantic serializes Decimal as a JSON string; procurement floats arrive as numbers.
export const apiDecimalSchema = z.union([z.number().finite(), decimalTextSchema]).pipe(z.number().finite());
export const apiUuidSchema = z.uuid();
export const apiDateTimeSchema = z.iso.datetime({ offset: true, local: true });
export const apiDateSchema = z.iso.date();
